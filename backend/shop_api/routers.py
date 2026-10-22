from decimal import Decimal
from datetime import datetime, timedelta, timezone
import hashlib
import re
import secrets

import bleach
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash, generate_password_hash

from .config import CARD_CIPHER, FRONTEND_URL
from .database import get_session
from .models import AuditLog, CartItem, Comment, CommentImage, DefaultAddress, Inventory, Order, OrderFulfillment, OrderItem, OrderNotification, PasswordResetToken, PaymentMethod, Product, User
from .notifications import deliver_order_notification
from .password_reset_email import send_password_reset_email
from .schemas import AddressInput, CardInput, CartInput, CommentInput, LoginInput, OrderInput, PasswordResetInput, PasswordResetRequestInput, RegisterInput, UpdateCartInput
from .security import active_user, card_fingerprint, issue_token, normalized_card_number
from .services import COMMENT_CLEANER, PASSWORD_RE, cart_payload, save_comment_image

router = APIRouter(prefix="/api")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
RESET_WINDOW = timedelta(minutes=30)


def normalized_email(value: str) -> str:
    email = value.strip().lower()
    if not EMAIL_RE.fullmatch(email):
        raise HTTPException(400, "请输入有效的邮箱地址")
    return email


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(data: RegisterInput, session: Session = Depends(get_session)):
    username = data.username.strip()
    email = normalized_email(data.email)
    if len(username) < 3 or not re.fullmatch(r"[A-Za-z0-9_]+", username): raise HTTPException(400, "账号须为至少 3 位的字母、数字或下划线")
    if data.password != data.confirmPassword or not PASSWORD_RE.fullmatch(data.password): raise HTTPException(400, "密码至少 9 位，且包含大小写字母、数字和特殊字符；两次输入必须一致")
    if session.scalar(select(User).where(User.username == username)): raise HTTPException(409, "该账号已被注册")
    if session.scalar(select(User).where(func.lower(User.email) == email)): raise HTTPException(409, "该邮箱已被注册")
    session.add(User(username=username, email=email, password_hash=generate_password_hash(data.password))); session.commit()
    return {"message": "注册成功"}


@router.post("/auth/login")
def login(data: LoginInput, session: Session = Depends(get_session)):
    identifier = data.username.strip()
    user = session.scalar(select(User).where(User.username == identifier))
    if not user:
        email_matches = session.scalars(select(User).where(func.lower(User.email) == identifier.lower())).all()
        user = next((candidate for candidate in email_matches if check_password_hash(candidate.password_hash, data.password)), None)
    if not user or not check_password_hash(user.password_hash, data.password): raise HTTPException(401, "账号、邮箱或密码错误")
    if user.status == "disabled": raise HTTPException(403, "该用户已停用")
    return {"token": issue_token(user), "user": {"id": user.id, "username": user.username, "role": user.role}}


@router.post("/auth/forgot-password")
def forgot_password(data: PasswordResetRequestInput, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    email = normalized_email(data.email)
    users = session.scalars(select(User).where(func.lower(User.email) == email, User.status == "active")).all()
    now = datetime.now(timezone.utc)
    deliveries: list[tuple[str, str, str]] = []
    for user in users:
        for stale_token in session.scalars(select(PasswordResetToken).where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))):
            stale_token.used_at = now
        raw_token = secrets.token_urlsafe(32)
        session.add(PasswordResetToken(user_id=user.id, token_hash=token_digest(raw_token), expires_at=now + RESET_WINDOW))
        deliveries.append((user.email, user.username, f"{FRONTEND_URL}/reset-password?token={raw_token}"))
    session.commit()
    for recipient, username, reset_url in deliveries:
        background_tasks.add_task(send_password_reset_email, recipient, username, reset_url)
    # This response is intentionally identical for unknown, disabled, and known accounts.
    return {"message": "如该邮箱已注册，重置链接将在几分钟内发送，请查收邮件。"}


@router.post("/auth/reset-password")
def reset_password(data: PasswordResetInput, session: Session = Depends(get_session)):
    if data.newPassword != data.confirmPassword or not PASSWORD_RE.fullmatch(data.newPassword):
        raise HTTPException(400, "密码至少 9 位，且包含大小写字母、数字和特殊字符；两次输入必须一致")
    reset_token = session.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_digest(data.token)))
    now = datetime.now(timezone.utc)
    if not reset_token or reset_token.used_at is not None or reset_token.expires_at.replace(tzinfo=timezone.utc) < now:
        raise HTTPException(400, "重置链接无效或已过期，请重新申请")
    user = session.get(User, reset_token.user_id)
    if not user:
        raise HTTPException(400, "重置链接无效或已过期，请重新申请")
    user.password_hash = generate_password_hash(data.newPassword)
    user.token_version += 1
    reset_token.used_at = now
    for other_token in session.scalars(select(PasswordResetToken).where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None), PasswordResetToken.id != reset_token.id)):
        other_token.used_at = now
    session.add(AuditLog(user_id=user.id, action="password_reset", detail="password reset by email", target_type="user", target_id=user.id))
    session.commit()
    return {"message": "密码已重置，请使用新密码登录"}


@router.get("/auth/me")
def me(user_id: int = Depends(active_user), session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user: raise HTTPException(401, "请先登录")
    return {"id": user.id, "username": user.username, "role": user.role}


@router.get("/products")
def products(session: Session = Depends(get_session)):
    return [{**product.serialize(), "stock": session.get(Inventory, product.id).quantity, "lowStock": 0 < session.get(Inventory, product.id).quantity <= 5} for product in session.scalars(select(Product).where(Product.status == "listed").order_by(Product.id))]


@router.get("/products/{product_id}")
def product_detail(product_id: int, session: Session = Depends(get_session)):
    product = session.get(Product, product_id)
    if not product or product.status != "listed": raise HTTPException(404, "商品不存在")
    stock = session.get(Inventory, product.id).quantity
    return {**product.serialize(), "stock": stock, "lowStock": 0 < stock <= 5}


@router.get("/products/{product_id}/comments")
def get_comments(product_id: int, session: Session = Depends(get_session)):
    if not session.get(Product, product_id): raise HTTPException(404, "商品不存在")
    return [comment.serialize() for comment in session.scalars(select(Comment).where(Comment.product_id == product_id).order_by(Comment.created_at.desc()))]


@router.post("/comment-images", status_code=status.HTTP_201_CREATED)
def upload_comment_image(request: Request, image: UploadFile = File(...), user_id: int = Depends(active_user), session: Session = Depends(get_session)):
    return save_comment_image(image, user_id, session, request.app.state.comment_upload_directory, str(request.base_url).rstrip("/"))


@router.post("/products/{product_id}/comments", status_code=status.HTTP_201_CREATED)
def create_comment(product_id: int, data: CommentInput, request: Request, user_id: int = Depends(active_user), session: Session = Depends(get_session)):
    product = session.get(Product, product_id); user = session.get(User, user_id)
    if not product or not user: raise HTTPException(404, "商品不存在")
    images = session.scalars(select(CommentImage).where(CommentImage.id.in_(data.imageIds), CommentImage.user_id == user_id, CommentImage.comment_id.is_(None))).all() if data.imageIds else []
    if len(images) != len(set(data.imageIds)): raise HTTPException(400, "评论图片无效或不属于当前账号")
    content = COMMENT_CLEANER.clean(data.content); text_content = bleach.clean(content, tags=[], strip=True).strip()
    allowed_urls = {image.serialize(str(request.base_url).rstrip("/"))["url"] for image in images}; embedded_urls = set(re.findall(r"<img[^>]+src=[\"']([^\"']+)[\"']", content))
    if embedded_urls != allowed_urls: raise HTTPException(400, "评论中的图片无效")
    if not text_content and not embedded_urls: raise HTTPException(400, "请输入评论内容")
    comment = Comment(product_id=product_id, user_id=user_id, author_name=user.username, content=content); session.add(comment); session.flush()
    for image in images: image.comment_id = comment.id
    session.commit(); session.refresh(comment); return comment.serialize()


@router.get("/account/address")
def get_default_address(user_id: int = Depends(active_user), session: Session = Depends(get_session)):
    address = session.scalar(select(DefaultAddress).where(DefaultAddress.user_id == user_id))
    return address.serialize() if address else None


@router.put("/account/address")
def save_default_address(data: AddressInput, user_id: int = Depends(active_user), session: Session = Depends(get_session)):
    address = session.scalar(select(DefaultAddress).where(DefaultAddress.user_id == user_id)); values = {"recipient_name": data.recipientName.strip(), "recipient_phone": data.recipientPhone, "province": data.province, "city": data.city, "district": data.district, "detail": data.detail.strip()}
    if address:
        for key, value in values.items(): setattr(address, key, value)
    else: address = DefaultAddress(user_id=user_id, **values); session.add(address)
    session.commit(); session.refresh(address); return address.serialize()


@router.get("/payment-methods")
def payment_methods(user_id: int = Depends(active_user), session: Session = Depends(get_session)):
    return [method.serialize() for method in session.scalars(select(PaymentMethod).where(PaymentMethod.user_id == user_id).order_by(PaymentMethod.created_at.desc()))]


@router.post("/payment-methods", status_code=status.HTTP_201_CREATED)
def add_payment_method(data: CardInput, user_id: int = Depends(active_user), session: Session = Depends(get_session)):
    number = normalized_card_number(data.cardNumber); fingerprint = card_fingerprint(number); existing = session.scalar(select(PaymentMethod).where(PaymentMethod.card_fingerprint == fingerprint))
    if existing:
        if existing.user_id == user_id: return existing.serialize()
        raise HTTPException(409, "该银行卡已被其他账号保存")
    method = PaymentMethod(user_id=user_id, encrypted_card_number=CARD_CIPHER.encrypt(number.encode()).decode(), card_fingerprint=fingerprint, last4=number[-4:])
    session.add(method); session.commit(); session.refresh(method); return method.serialize()


@router.get("/cart")
def get_cart(user_id: int = Depends(active_user), session: Session = Depends(get_session)): return cart_payload(session, user_id)


@router.post("/cart", status_code=status.HTTP_201_CREATED)
def add_cart(data: CartInput, user_id: int = Depends(active_user), session: Session = Depends(get_session)):
    product = session.get(Product, data.productId)
    if not product or product.status != "listed": raise HTTPException(409, "商品已下架，无法加入购物车")
    item = session.scalar(select(CartItem).where(CartItem.user_id == user_id, CartItem.product_id == data.productId))
    if item: item.quantity += data.quantity
    else: session.add(CartItem(user_id=user_id, product_id=data.productId, quantity=data.quantity))
    session.commit(); return cart_payload(session, user_id)


@router.patch("/cart/{item_id}")
def update_cart(item_id: int, data: UpdateCartInput, user_id: int = Depends(active_user), session: Session = Depends(get_session)):
    item = session.get(CartItem, item_id)
    if not item or item.user_id != user_id: raise HTTPException(404, "购物车条目不存在")
    item.quantity = data.quantity; session.commit(); return cart_payload(session, user_id)


@router.delete("/cart/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cart(item_id: int, user_id: int = Depends(active_user), session: Session = Depends(get_session)):
    item = session.get(CartItem, item_id)
    if not item or item.user_id != user_id: raise HTTPException(404, "购物车条目不存在")
    session.delete(item); session.commit()


@router.post("/orders", status_code=status.HTTP_201_CREATED)
def create_order(data: OrderInput, request: Request, background_tasks: BackgroundTasks, user_id: int = Depends(active_user), session: Session = Depends(get_session)):
    options = {"pickup": ("线下自提", Decimal("0")), "sf": ("顺丰次日达", Decimal("5")), "yto": ("圆通快递", Decimal("0")), "guotong": ("国通快递", Decimal("0")), "sto": ("申通快递", Decimal("0")), "yunda": ("韵达快递", Decimal("0")), "standard": ("圆通快递", Decimal("0"))}
    if data.deliveryService not in options: raise HTTPException(400, "配送方式无效")
    if data.paymentType not in {"wechat", "alipay", "bank_card"}: raise HTTPException(400, "支付方式无效")
    # The web checkout always sends an address for courier delivery. Keeping this
    # optional here preserves compatibility for older API clients during rollout.
    payment_last4 = None
    if data.paymentType == "bank_card":
        method = session.get(PaymentMethod, data.paymentMethodId)
        if not method or method.user_id != user_id: raise HTTPException(400, "请选择已保存的银行卡")
        payment_last4 = method.last4
    items = session.scalars(select(CartItem).where(CartItem.user_id == user_id, CartItem.id.in_(data.itemIds)).with_for_update()).all()
    if not items: raise HTTPException(400, "请选择要结算的商品")
    try:
        service_name, fee = options[data.deliveryService]; total = fee
        for item in items:
            product = session.get(Product, item.product_id, with_for_update=True)
            if product.status != "listed": raise ValueError("商品已下架，无法提交订单")
            stock = session.get(Inventory, item.product_id, with_for_update=True)
            if stock.quantity < item.quantity: raise ValueError(f"{item.product.name} 库存不足")
            stock.quantity -= item.quantity; total += item.product.price * item.quantity
        order = Order(user_id=user_id, total=total); session.add(order); session.flush(); address = data.address
        session.add(OrderFulfillment(order_id=order.id, delivery_service=service_name, delivery_fee=fee, recipient_name=address.recipientName.strip() if address else None, recipient_phone=address.recipientPhone if address else None, province=address.province if address else None, city=address.city if address else None, district=address.district if address else None, detail=address.detail.strip() if address else None, pickup_store="常州市天宁区文化广场小行星桌游社" if data.deliveryService == "pickup" else None, pickup_phone="+86-12345678901" if data.deliveryService == "pickup" else None, payment_type={"wechat": "微信支付", "alipay": "支付宝", "bank_card": "银行卡"}[data.paymentType], payment_last4=payment_last4))
        for item in items: session.add(OrderItem(order_id=order.id, product_name=item.product.name, unit_price=item.product.price, quantity=item.quantity)); session.delete(item)
        session.add(OrderNotification(order_id=order.id))
        session.add(AuditLog(user_id=user_id, action="order_created", detail=str(order.id))); session.commit(); session.refresh(order)
        if request.app.state.notifications_enabled:
            background_tasks.add_task(deliver_order_notification, order.id, request.app.state.sessions)
        return order.serialize()
    except ValueError as error:
        session.rollback(); raise HTTPException(409, str(error)) from error


@router.get("/orders/{order_id}")
def get_order(order_id: int, user_id: int = Depends(active_user), session: Session = Depends(get_session)):
    order = session.get(Order, order_id)
    if not order or order.user_id != user_id: raise HTTPException(404, "订单不存在")
    return order.serialize()
