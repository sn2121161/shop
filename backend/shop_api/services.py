import re
from pathlib import Path
from uuid import uuid4

import bleach
from bleach.css_sanitizer import CSSSanitizer
from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from werkzeug.security import generate_password_hash

from .models import CartItem, Comment, CommentImage, Inventory, Product, User

PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{9,}$")
COMMENT_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
COMMENT_CLEANER = bleach.Cleaner(tags={"p", "br", "div", "span", "strong", "b", "em", "i", "u", "img"}, attributes={"span": ["style"], "div": ["style"], "img": ["src", "alt"]}, css_sanitizer=CSSSanitizer(allowed_css_properties=["color"]), strip=True)
PRODUCTS = [("苯", 10, "六角环的平衡感", "以稳定的芳香环为轮廓，把秩序藏进一枚轻巧的日常项链。"), ("尼古丁", 15, "连接与分岔", "用分子骨架的转折，记录好奇心在不同方向之间游走的瞬间。"), ("血清素", 12, "温柔的信号", "把与快乐有关的化学讯号化成可佩戴线条，提醒自己留意微小的明亮。"), ("肾上腺素", 18, "跃动的坐标", "不规则的侧链像一次出发前的心跳，为日常增加一点大胆的节奏。"), ("咖啡因", 17, "清醒的几何", "交织的环状结构带来简洁的理性美感，献给每一个专注的清晨。"), ("可卡因", 20, "结构研究 I", "仅取其分子结构的曲线作为艺术研究对象，呈现复杂骨架的视觉张力。"), ("海洛因I型", 12, "结构研究 II", "以化学结构史为灵感的线条练习，不关联任何物质的使用或获取。"), ("LSD", 20, "微观的想象", "将实验室图谱般的分叉转为首饰语言，保留抽象与未知的空间。"), ("吗啡", 25, "结构研究 III", "多环的层次被简化为佩戴尺度的线条，只讨论化学图形的美学。"), ("地巴唑", 28, "双环对话", "两个环相遇又留白，像是一次安静却完整的视觉对话。"), ("戊巴比妥", 28, "秩序的节拍", "重复的连接点让结构像一段节拍，适合喜欢细节的人。"), ("薄荷醇", 21, "清凉的弧线", "从自然分子的立体转折取形，做成轻盈、清爽的流线。"), ("乙醇", 11, "最小的诗", "用极简的双碳骨架证明：简单的结构也能讲述完整的故事。"), ("THC", 25, "结构研究 IV", "将复杂环系抽象成首饰轮廓，作品仅服务于分子图形的观察。"), ("迷幻剂", 30, "想象的折线", "以“感知的边界”为主题进行的抽象系列，不指向任何实际物质。"), ("海洛因II型", 20, "结构研究 V", "延续化学骨架的艺术转译，强调科学图谱与工艺之间的距离感。"), ("裸盖菇素", 15, "自然的分支", "从自然界化合物的分支感获得灵感，做成有机而克制的线条。")]


def cart_payload(session: Session, user_id: int):
    return [{"id": item.id, "product": item.product.serialize(), "quantity": item.quantity, "stock": session.get(Inventory, item.product_id).quantity} for item in session.scalars(select(CartItem).where(CartItem.user_id == user_id))]


def save_comment_image(image: UploadFile, user_id: int, session: Session, directory: Path, base_url: str) -> dict:
    if image.content_type not in COMMENT_IMAGE_TYPES: raise HTTPException(400, "仅支持 JPG、PNG、WebP 或 GIF 图片")
    contents = image.file.read()
    if not contents or len(contents) > 5 * 1024 * 1024: raise HTTPException(400, "图片需小于 5MB")
    filename = f"{uuid4().hex}{COMMENT_IMAGE_TYPES[image.content_type]}"; path = f"/uploads/comments/{filename}"
    (directory / filename).write_bytes(contents)
    uploaded = CommentImage(user_id=user_id, path=path); session.add(uploaded); session.commit(); session.refresh(uploaded)
    return uploaded.serialize(base_url)


def save_product_image(image: UploadFile, directory: Path) -> str:
    if image.content_type not in COMMENT_IMAGE_TYPES: raise HTTPException(400, "仅支持 JPG、PNG、WebP 或 GIF 图片")
    contents = image.file.read()
    if not contents or len(contents) > 5 * 1024 * 1024: raise HTTPException(400, "图片需小于 5MB")
    filename = f"{uuid4().hex}{COMMENT_IMAGE_TYPES[image.content_type]}"
    (directory / filename).write_bytes(contents)
    return f"/uploads/products/{filename}"


def seed_database(sessions: sessionmaker[Session]) -> None:
    with sessions() as session:
        admin = session.scalar(select(User).where(User.username == "admin"))
        if not admin:
            # The requested bootstrap credential is hashed and never exposed by an API.
            session.add(User(username="admin", password_hash=generate_password_hash("Admin@123"), role="admin"))
            session.commit()
        if not session.scalar(select(Product.id).limit(1)):
            for name, price, tagline, story in PRODUCTS:
                product = Product(name=name, price=price, tagline=tagline, story=story); session.add(product); session.flush(); session.add(Inventory(product_id=product.id, quantity=12))
            session.commit()
        if session.scalar(select(Comment.id).limit(1)): return
        reviewers = {}
        for username in ("structure_lover", "quiet_maker", "blue_molecule"):
            reviewer = session.scalar(select(User).where(User.username == username))
            if not reviewer: reviewer = User(username=username, password_hash=generate_password_hash(uuid4().hex)); session.add(reviewer); session.flush()
            reviewers[username] = reviewer
        for product_name, username, content in (("苯", "structure_lover", "<p><strong>苯环的线条很干净</strong>，金属边缘在光线下特别有层次。</p>"), ("血清素", "quiet_maker", "<p><span style=\"color:#265842\">血清素这件很温柔</span>，日常搭配也不会太张扬。</p>"), ("可卡因", "blue_molecule", "<p><em>把复杂结构做成首饰很有意思</em>，深蓝色细节让轮廓更清楚。</p>")):
            product = session.scalar(select(Product).where(Product.name == product_name))
            if product: session.add(Comment(product_id=product.id, user_id=reviewers[username].id, author_name=username, content=content))
        session.commit()
