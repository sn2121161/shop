"""Persist provider subscriptions and push snapshots."""
from alembic import op
import sqlalchemy as sa

revision = "20261027_04"
down_revision = "20261017_03"
branch_labels = None
depends_on = None


def upgrade():
    # The legacy initial migration builds current metadata on fresh installations.
    if sa.inspect(op.get_bind()).has_table("tracking_subscriptions", schema="shop"):
        return
    op.create_table("tracking_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("courier", sa.String(), nullable=False),
        sa.Column("waybill", sa.String(), nullable=False),
        sa.Column("subscription_status", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("traces", sa.String(), nullable=False),
        sa.Column("push_time", sa.String()),
        sa.Column("updated_at", sa.String()),
        sa.Column("last_push_at", sa.String()),
        sa.UniqueConstraint("courier", "waybill"), schema="shop")


def downgrade():
    op.drop_table("tracking_subscriptions", schema="shop")
