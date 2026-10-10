"""create initial shop schema

Revision ID: 20261009_01
Revises:
Create Date: 2026-10-09
"""
from alembic import op

from shop_api.database import Base
import shop_api.models  # noqa: F401

revision = "20261009_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("CREATE SCHEMA IF NOT EXISTS shop")
    Base.metadata.create_all(bind=bind)
    for statement in (
        "CREATE INDEX IF NOT EXISTS ix_shop_orders_created_at ON shop.orders (created_at)",
        "CREATE INDEX IF NOT EXISTS ix_shop_orders_user_id ON shop.orders (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_shop_order_items_order_id ON shop.order_items (order_id)",
        "CREATE INDEX IF NOT EXISTS ix_shop_order_fulfillments_delivery_service ON shop.order_fulfillments (delivery_service)",
        "CREATE INDEX IF NOT EXISTS ix_shop_products_status ON shop.products (status)",
        "CREATE INDEX IF NOT EXISTS ix_shop_users_status ON shop.users (status)",
    ):
        op.execute(statement)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
    op.execute("DROP SCHEMA IF EXISTS shop CASCADE")
