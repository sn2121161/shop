"""set requested account email defaults

Revision ID: 20261017_03
Revises: 20261016_02
Create Date: 2026-10-17
"""
from alembic import op


revision = "20261017_03"
down_revision = "20261016_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE shop.users SET email = CASE "
        "WHEN role = 'admin' THEN '1136205530@qq.com' "
        "ELSE 'nizhengwen@126.com' END"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE shop.users SET email = CASE "
        "WHEN role = 'admin' THEN 'nizhengwen@126.com' "
        "ELSE '1136205530@qq.com' END"
    )
