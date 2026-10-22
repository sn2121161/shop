from collections.abc import Generator

from fastapi import Request
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


def build_engine(database_url: str):
    options = {"future": True}
    if database_url == "sqlite://":
        options.update(connect_args={"check_same_thread": False}, poolclass=StaticPool)
    engine = create_engine(database_url, **options)
    return engine.execution_options(schema_translate_map={"shop": None}) if database_url.startswith("sqlite") else engine


def create_schema(engine, database_url: str) -> None:
    if not database_url.startswith("sqlite"):
        with engine.begin() as connection:
            connection.execute(text("CREATE SCHEMA IF NOT EXISTS shop"))


def migrate_schema(engine, database_url: str) -> None:
    """Additive migration for installations created before the merchant console."""
    if database_url.startswith("sqlite"):
        with engine.begin() as connection:
            columns = {row[1] for row in connection.execute(text("PRAGMA table_info(users)"))}
            if "email" not in columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR"))
                connection.execute(text("UPDATE users SET email = CASE WHEN role = 'admin' THEN '1136205530@qq.com' ELSE 'nizhengwen@126.com' END WHERE email IS NULL"))
            if "token_version" not in columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0"))
        return
    statements = (
        "ALTER TABLE shop.users ADD COLUMN IF NOT EXISTS status VARCHAR NOT NULL DEFAULT 'active'",
        "ALTER TABLE shop.products ADD COLUMN IF NOT EXISTS image_path VARCHAR",
        "ALTER TABLE shop.products ADD COLUMN IF NOT EXISTS status VARCHAR NOT NULL DEFAULT 'listed'",
        "ALTER TABLE shop.audit_logs ADD COLUMN IF NOT EXISTS target_type VARCHAR",
        "ALTER TABLE shop.audit_logs ADD COLUMN IF NOT EXISTS target_id INTEGER",
        "ALTER TABLE shop.audit_logs ADD COLUMN IF NOT EXISTS before_value TEXT",
        "ALTER TABLE shop.audit_logs ADD COLUMN IF NOT EXISTS after_value TEXT",
        "CREATE INDEX IF NOT EXISTS ix_shop_orders_created_at ON shop.orders (created_at)",
        "CREATE INDEX IF NOT EXISTS ix_shop_orders_user_id ON shop.orders (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_shop_order_items_order_id ON shop.order_items (order_id)",
        "CREATE INDEX IF NOT EXISTS ix_shop_order_fulfillments_delivery_service ON shop.order_fulfillments (delivery_service)",
        "CREATE INDEX IF NOT EXISTS ix_shop_products_status ON shop.products (status)",
        "CREATE INDEX IF NOT EXISTS ix_shop_users_status ON shop.users (status)",
    )
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def get_session(request: Request) -> Generator[Session, None, None]:
    with request.app.state.sessions() as session:
        yield session
