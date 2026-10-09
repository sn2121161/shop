from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"; __table_args__ = {"schema": "shop"}
    id: Mapped[int] = mapped_column(primary_key=True); username: Mapped[str] = mapped_column(unique=True); password_hash: Mapped[str]; role: Mapped[str] = mapped_column(default="customer"); status: Mapped[str] = mapped_column(default="active"); created_at: Mapped[datetime] = mapped_column(default=utcnow)


class DefaultAddress(Base):
    __tablename__ = "default_addresses"; __table_args__ = {"schema": "shop"}
    id: Mapped[int] = mapped_column(primary_key=True); user_id: Mapped[int] = mapped_column(ForeignKey("shop.users.id"), unique=True); recipient_name: Mapped[str]; recipient_phone: Mapped[str]; province: Mapped[str]; city: Mapped[str]; district: Mapped[str]; detail: Mapped[str]; updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
    def serialize(self): return {"recipientName": self.recipient_name, "recipientPhone": self.recipient_phone, "province": self.province, "city": self.city, "district": self.district, "detail": self.detail}


class PaymentMethod(Base):
    __tablename__ = "payment_methods"; __table_args__ = {"schema": "shop"}
    id: Mapped[int] = mapped_column(primary_key=True); user_id: Mapped[int] = mapped_column(ForeignKey("shop.users.id")); encrypted_card_number: Mapped[str]; card_fingerprint: Mapped[str] = mapped_column(unique=True); last4: Mapped[str]; card_brand: Mapped[str] = mapped_column(default="银行卡"); created_at: Mapped[datetime] = mapped_column(default=utcnow)
    def serialize(self): return {"id": self.id, "label": f"{self.card_brand} · {self.last4}", "last4": self.last4}


class Product(Base):
    __tablename__ = "products"; __table_args__ = {"schema": "shop"}
    id: Mapped[int] = mapped_column(primary_key=True); name: Mapped[str] = mapped_column(unique=True); price: Mapped[Decimal]; tagline: Mapped[str] = mapped_column(default=""); story: Mapped[str] = mapped_column(default=""); image_path: Mapped[str | None]; status: Mapped[str] = mapped_column(default="listed")
    def serialize(self): return {"id": self.id, "name": self.name, "price": float(self.price), "tagline": self.tagline, "story": self.story, "image": self.image_path or "/images/product.jpg", "status": self.status}


class Inventory(Base):
    __tablename__ = "inventory"; __table_args__ = (CheckConstraint("quantity >= 0", name="quantity_nonnegative"), {"schema": "shop"})
    product_id: Mapped[int] = mapped_column(ForeignKey("shop.products.id"), primary_key=True); quantity: Mapped[int] = mapped_column(default=12)


class CartItem(Base):
    __tablename__ = "cart_items"; __table_args__ = (UniqueConstraint("user_id", "product_id"), {"schema": "shop"})
    id: Mapped[int] = mapped_column(primary_key=True); user_id: Mapped[int] = mapped_column(ForeignKey("shop.users.id")); product_id: Mapped[int] = mapped_column(ForeignKey("shop.products.id")); quantity: Mapped[int] = mapped_column(default=1); product: Mapped[Product] = relationship()


class Order(Base):
    __tablename__ = "orders"; __table_args__ = {"schema": "shop"}
    id: Mapped[int] = mapped_column(primary_key=True); user_id: Mapped[int] = mapped_column(ForeignKey("shop.users.id")); total: Mapped[Decimal]; status: Mapped[str] = mapped_column(default="created"); created_at: Mapped[datetime] = mapped_column(default=utcnow); customer: Mapped[User] = relationship(); items: Mapped[list["OrderItem"]] = relationship(cascade="all, delete-orphan"); fulfillment: Mapped["OrderFulfillment | None"] = relationship(cascade="all, delete-orphan", uselist=False); notification: Mapped["OrderNotification | None"] = relationship(cascade="all, delete-orphan", uselist=False)
    def serialize(self): return {"id": self.id, "total": float(self.total), "status": self.status, "createdAt": self.created_at.isoformat(), "customerAccount": self.customer.username if self.customer else None, "items": [item.serialize() for item in self.items], "fulfillment": self.fulfillment.serialize() if self.fulfillment else None, "notificationStatus": self.notification.status if self.notification else None}


class OrderItem(Base):
    __tablename__ = "order_items"; __table_args__ = {"schema": "shop"}
    id: Mapped[int] = mapped_column(primary_key=True); order_id: Mapped[int] = mapped_column(ForeignKey("shop.orders.id")); product_name: Mapped[str]; unit_price: Mapped[Decimal]; quantity: Mapped[int]
    def serialize(self): return {"name": self.product_name, "unitPrice": float(self.unit_price), "quantity": self.quantity}


class OrderFulfillment(Base):
    __tablename__ = "order_fulfillments"; __table_args__ = {"schema": "shop"}
    id: Mapped[int] = mapped_column(primary_key=True); order_id: Mapped[int] = mapped_column(ForeignKey("shop.orders.id"), unique=True); delivery_service: Mapped[str]; delivery_fee: Mapped[Decimal]; recipient_name: Mapped[str | None]; recipient_phone: Mapped[str | None]; province: Mapped[str | None]; city: Mapped[str | None]; district: Mapped[str | None]; detail: Mapped[str | None]; pickup_store: Mapped[str | None]; pickup_phone: Mapped[str | None]; payment_type: Mapped[str]; payment_last4: Mapped[str | None]
    def serialize(self): return {"deliveryService": self.delivery_service, "deliveryFee": float(self.delivery_fee), "recipientName": self.recipient_name, "recipientPhone": self.recipient_phone, "province": self.province, "city": self.city, "district": self.district, "detail": self.detail, "pickupStore": self.pickup_store, "pickupPhone": self.pickup_phone, "paymentType": self.payment_type, "paymentLast4": self.payment_last4}


class OrderNotification(Base):
    __tablename__ = "order_notifications"; __table_args__ = {"schema": "shop"}
    id: Mapped[int] = mapped_column(primary_key=True); order_id: Mapped[int] = mapped_column(ForeignKey("shop.orders.id"), unique=True); status: Mapped[str] = mapped_column(default="pending"); attempt_count: Mapped[int] = mapped_column(default=0); last_error: Mapped[str | None]; notified_at: Mapped[datetime | None]; created_at: Mapped[datetime] = mapped_column(default=utcnow); updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"; __table_args__ = {"schema": "shop"}
    id: Mapped[int] = mapped_column(primary_key=True); user_id: Mapped[int | None]; action: Mapped[str]; detail: Mapped[str | None]; target_type: Mapped[str | None]; target_id: Mapped[int | None]; before_value: Mapped[str | None]; after_value: Mapped[str | None]; created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Comment(Base):
    __tablename__ = "comments"; __table_args__ = {"schema": "shop"}
    id: Mapped[int] = mapped_column(primary_key=True); product_id: Mapped[int] = mapped_column(ForeignKey("shop.products.id")); user_id: Mapped[int] = mapped_column(ForeignKey("shop.users.id")); author_name: Mapped[str]; content: Mapped[str]; created_at: Mapped[datetime] = mapped_column(default=utcnow); images: Mapped[list["CommentImage"]] = relationship(cascade="all, delete-orphan")
    def serialize(self): return {"id": self.id, "author": self.author_name, "content": self.content, "createdAt": self.created_at.isoformat()}


class CommentImage(Base):
    __tablename__ = "comment_images"; __table_args__ = {"schema": "shop"}
    id: Mapped[int] = mapped_column(primary_key=True); user_id: Mapped[int] = mapped_column(ForeignKey("shop.users.id")); comment_id: Mapped[int | None] = mapped_column(ForeignKey("shop.comments.id")); path: Mapped[str] = mapped_column(unique=True); created_at: Mapped[datetime] = mapped_column(default=utcnow)
    def serialize(self, base_url: str): return {"id": self.id, "url": f"{base_url}{self.path}"}
