"""Merchant-console endpoints. All mutations are atomic and audited."""

import json
from datetime import date, datetime, time, timezone
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .database import get_session
from .models import AuditLog, DefaultAddress, Inventory, Order, Product, User
from .schemas import PriceInput, ProductCreateInput, ProductRelistInput, StockInput
from .security import current_admin
from .services import save_product_image

admin_router = APIRouter(prefix="/api/admin", tags=["admin"])
SHANGHAI = ZoneInfo("Asia/Shanghai")


def audit(session: Session, admin_id: int, action: str, target_type: str, target_id: int, before: dict | None = None, after: dict | None = None, detail: str | None = None) -> None:
    session.add(AuditLog(user_id=admin_id, action=action, detail=detail, target_type=target_type, target_id=target_id, before_value=json.dumps(before, ensure_ascii=False) if before else None, after_value=json.dumps(after, ensure_ascii=False) if after else None))


def product_payload(product: Product, inventory: Inventory) -> dict:
    payload = product.serialize()
    payload.update({"stock": inventory.quantity, "inventoryStatus": "out_of_stock" if inventory.quantity == 0 else "normal", "lowStock": inventory.quantity <= 5})
    return payload


def shanghai_date(value: datetime) -> date:
    return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value).astimezone(SHANGHAI).date()


def order_bounds(start: date, end: date) -> tuple[datetime, datetime]:
    return datetime.combine(start, time.min, tzinfo=SHANGHAI).astimezone(timezone.utc), datetime.combine(end, time.max, tzinfo=SHANGHAI).astimezone(timezone.utc)


def order_range(session: Session, start: date, end: date) -> list[Order]:
    lower, upper = order_bounds(start, end)
    return session.scalars(select(Order).options(selectinload(Order.customer), selectinload(Order.items), selectinload(Order.fulfillment)).where(Order.created_at >= lower, Order.created_at <= upper).order_by(Order.created_at.desc())).all()


def order_totals(session: Session, start: date, end: date) -> tuple[int, Decimal]:
    lower, upper = order_bounds(start, end)
    count, sales = session.execute(select(func.count(Order.id), func.coalesce(func.sum(Order.total), 0)).where(Order.created_at >= lower, Order.created_at <= upper)).one()
    return count, Decimal(sales)


@admin_router.get("/dashboard")
def dashboard(
    start: date | None = None, end: date | None = None, username: str = "", product: str = "", delivery_service: str = "", page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), _: int = Depends(current_admin), session: Session = Depends(get_session),
):
    today = datetime.now(SHANGHAI).date()
    end = end or today
    start = start or (end.fromordinal(end.toordinal() - 29))
    if start > end: raise HTTPException(400, "开始日期不能晚于结束日期")
    orders = order_range(session, start, end)
    products = {item.name: item for item in session.scalars(select(Product))}
    stocks = {item.product_id: item.quantity for item in session.scalars(select(Inventory))}
    active_users = session.scalar(select(func.count()).select_from(User).where(User.status == "active", User.role != "admin")) or 0
    listed_products = session.scalars(select(Product).where(Product.status == "listed")).all()
    today_count, today_sales = order_totals(session, today, today)
    _, total_sales = session.execute(select(func.count(Order.id), func.coalesce(func.sum(Order.total), 0))).one()
    days = [start.fromordinal(start.toordinal() + offset) for offset in range((end - start).days + 1)]
    orders_by_day: dict[date, list[Order]] = {}
    for order in orders:
        orders_by_day.setdefault(shanghai_date(order.created_at), []).append(order)
    trend = [{"date": day.isoformat(), "orders": len(orders_by_day.get(day, [])), "sales": float(sum((order.total for order in orders_by_day.get(day, [])), Decimal("0")))} for day in days]
    users: dict[int, dict] = {}
    products_sold: dict[str, dict] = {}

    def current_items(order: Order) -> list[dict]:
        rows = []
        for item in order.items:
            current_product = products.get(item.product_name)
            rows.append({"name": item.product_name, "quantity": item.quantity, "unitPrice": float(item.unit_price), "currentStock": stocks.get(current_product.id) if current_product else None})
        return rows

    def delivery_name(order: Order) -> str:
        """Legacy orders can predate the fulfillment record; keep them visible."""
        return order.fulfillment.delivery_service if order.fulfillment else "未填写配送服务"

    # Rank tables always reflect the selected date range, not the detail-only filters.
    for order in orders:
        customer = order.customer
        summary = users.setdefault(customer.id, {"username": customer.username, "orderCount": 0, "unitsBought": 0, "sales": Decimal("0")})
        summary["orderCount"] += 1; summary["unitsBought"] += sum(item.quantity for item in order.items); summary["sales"] += order.total
        for item in current_items(order):
            aggregate = products_sold.setdefault(item["name"], {"product": item["name"], "unitsSold": 0, "sales": Decimal("0"), "currentStock": item["currentStock"]})
            aggregate["unitsSold"] += item["quantity"]; aggregate["sales"] += Decimal(str(item["unitPrice"])) * item["quantity"]

    detail_rows = []
    for order in orders:
        customer = order.customer
        if username and username.lower() not in customer.username.lower(): continue
        if delivery_service and delivery_name(order) != delivery_service: continue
        if product and not any(product.lower() in item.product_name.lower() for item in order.items): continue
        detail_rows.append({"id": order.id, "createdAt": order.created_at.isoformat(), "username": customer.username, "deliveryService": delivery_name(order), "total": float(order.total), "items": current_items(order)})
    total_details = len(detail_rows)
    detail_rows = detail_rows[(page - 1) * page_size: page * page_size]
    return {
        "range": {"start": start.isoformat(), "end": end.isoformat()},
        "summary": {"todayOrders": today_count, "todaySales": float(today_sales), "totalSales": float(Decimal(total_sales)), "activeUsers": active_users, "listedProducts": len(listed_products), "outOfStockProducts": sum(stocks.get(item.id, 0) == 0 for item in listed_products), "lowStockProducts": sum(0 < stocks.get(item.id, 0) <= 5 for item in listed_products)},
        "trend": trend,
        "users": [{**row, "sales": float(row["sales"])} for row in sorted(users.values(), key=lambda row: row["sales"], reverse=True)],
        "products": [{**row, "sales": float(row["sales"])} for row in sorted(products_sold.values(), key=lambda row: row["unitsSold"], reverse=True)],
        "details": {"items": detail_rows, "total": total_details, "page": page, "pageSize": page_size},
    }


@admin_router.get("/users")
def list_users(
    status: str = Query("active", pattern="^(active|disabled)$"), username: str = "", created_from: str | None = None, created_to: str | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), _: int = Depends(current_admin), session: Session = Depends(get_session),
):
    query = select(User).where(User.status == status)
    if username.strip(): query = query.where(User.username.ilike(f"%{username.strip()}%"))
    if created_from: query = query.where(User.created_at >= created_from)
    if created_to: query = query.where(User.created_at <= f"{created_to}T23:59:59+00:00")
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    users = session.scalars(query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    addresses = {address.user_id: address for address in session.scalars(select(DefaultAddress).where(DefaultAddress.user_id.in_([user.id for user in users])))} if users else {}
    return {"items": [{"id": user.id, "username": user.username, "role": user.role, "status": user.status, "createdAt": user.created_at.isoformat(), "defaultAddress": addresses[user.id].serialize() if user.id in addresses else None} for user in users], "total": total, "page": page, "pageSize": page_size}


@admin_router.post("/users/{user_id}/disable")
def disable_user(user_id: int, admin_id: int = Depends(current_admin), session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user: raise HTTPException(404, "用户不存在")
    if user.role == "admin": raise HTTPException(400, "系统管理员不可停用")
    if user.status == "disabled": return {"message": "用户已停用"}
    before = {"status": user.status}; user.status = "disabled"; audit(session, admin_id, "user_disabled", "user", user.id, before, {"status": user.status}); session.commit()
    return {"message": "用户已停用"}


@admin_router.post("/users/{user_id}/restore")
def restore_user(user_id: int, admin_id: int = Depends(current_admin), session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user: raise HTTPException(404, "用户不存在")
    if user.role == "admin": raise HTTPException(400, "系统管理员无需恢复")
    if user.status == "active": return {"message": "用户已启用"}
    before = {"status": user.status}; user.status = "active"; audit(session, admin_id, "user_restored", "user", user.id, before, {"status": user.status}); session.commit()
    return {"message": "用户已恢复"}


@admin_router.get("/products")
def list_products(
    status: str = Query("listed", pattern="^(listed|unlisted)$"), keyword: str = "", page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), _: int = Depends(current_admin), session: Session = Depends(get_session),
):
    query = select(Product, Inventory).join(Inventory).where(Product.status == status)
    if keyword.strip(): query = query.where(Product.name.ilike(f"%{keyword.strip()}%"))
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = session.execute(query.order_by(Inventory.quantity.asc(), Product.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [product_payload(product, inventory) for product, inventory in rows], "total": total, "page": page, "pageSize": page_size}


@admin_router.post("/products/images")
def upload_product_image(request: Request, image: UploadFile = File(...), _: int = Depends(current_admin)):
    return {"path": save_product_image(image, request.app.state.product_upload_directory)}


@admin_router.post("/products")
def create_product(data: ProductCreateInput, admin_id: int = Depends(current_admin), session: Session = Depends(get_session)):
    if session.scalar(select(Product).where(Product.name == data.name.strip())): raise HTTPException(409, "商品名称已存在")
    product = Product(name=data.name.strip(), price=data.price.quantize(Decimal("0.01")), tagline=data.tagline.strip(), story=data.story.strip(), image_path=data.imagePath, status="listed")
    session.add(product); session.flush(); inventory = Inventory(product_id=product.id, quantity=data.quantity); session.add(inventory)
    audit(session, admin_id, "product_created", "product", product.id, after={"name": product.name, "price": str(product.price), "quantity": inventory.quantity}); session.commit()
    return product_payload(product, inventory)


@admin_router.post("/products/{product_id}/restock")
def restock_product(product_id: int, data: StockInput, admin_id: int = Depends(current_admin), session: Session = Depends(get_session)):
    inventory = session.get(Inventory, product_id)
    if not inventory: raise HTTPException(404, "商品不存在")
    before = {"quantity": inventory.quantity}; inventory.quantity += data.quantity
    audit(session, admin_id, "product_restocked", "product", product_id, before, {"quantity": inventory.quantity}); session.commit()
    return product_payload(session.get(Product, product_id), inventory)


@admin_router.post("/products/{product_id}/unlist")
def unlist_product(product_id: int, reason: str = "", admin_id: int = Depends(current_admin), session: Session = Depends(get_session)):
    product = session.get(Product, product_id)
    if not product: raise HTTPException(404, "商品不存在")
    before = {"status": product.status}; product.status = "unlisted"; audit(session, admin_id, "product_unlisted", "product", product_id, before, {"status": product.status}, reason.strip() or None); session.commit()
    return {"message": "商品已下架"}


@admin_router.post("/products/{product_id}/relist")
def relist_product(product_id: int, data: ProductRelistInput, admin_id: int = Depends(current_admin), session: Session = Depends(get_session)):
    product = session.get(Product, product_id); inventory = session.get(Inventory, product_id)
    if not product or not inventory: raise HTTPException(404, "商品不存在")
    before = {"status": product.status, "price": str(product.price), "quantity": inventory.quantity}; product.status = "listed"; product.price = data.price.quantize(Decimal("0.01")); inventory.quantity = data.quantity
    audit(session, admin_id, "product_relisted", "product", product_id, before, {"status": product.status, "price": str(product.price), "quantity": inventory.quantity}); session.commit()
    return product_payload(product, inventory)


@admin_router.post("/products/{product_id}/price")
def update_price(product_id: int, data: PriceInput, admin_id: int = Depends(current_admin), session: Session = Depends(get_session)):
    product = session.get(Product, product_id)
    if not product: raise HTTPException(404, "商品不存在")
    if data.price is None and (data.percent is None or data.direction not in {"up", "down"}): raise HTTPException(400, "请输入价格或选择调价比例")
    before = {"price": str(product.price)}
    value = data.price if data.price is not None else product.price * (Decimal("1") + (Decimal(data.percent) / 100 if data.direction == "up" else -Decimal(data.percent) / 100))
    if value <= 0: raise HTTPException(400, "调整后的价格必须大于 0")
    product.price = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP); audit(session, admin_id, "product_price_changed", "product", product_id, before, {"price": str(product.price)}); session.commit()
    return {"price": float(product.price)}


@admin_router.get("/audit-logs")
def audit_logs(page: int = Query(1, ge=1), page_size: int = Query(30, ge=1, le=100), _: int = Depends(current_admin), session: Session = Depends(get_session)):
    total = session.scalar(select(func.count()).select_from(AuditLog)) or 0
    records = session.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [{"id": row.id, "action": row.action, "targetType": row.target_type, "targetId": row.target_id, "before": row.before_value, "after": row.after_value, "detail": row.detail, "createdAt": row.created_at.isoformat()} for row in records], "total": total}
