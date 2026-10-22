"""add user emails and password reset tokens

Revision ID: 20261016_02
Revises: 20261009_01
Create Date: 2026-10-16
"""
from alembic import op


revision = "20261016_02"
down_revision = "20261009_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE shop.users ADD COLUMN IF NOT EXISTS email VARCHAR")
    op.execute("UPDATE shop.users SET email = CASE WHEN role = 'admin' THEN '1136205530@qq.com' ELSE 'nizhengwen@126.com' END WHERE email IS NULL")
    op.execute("ALTER TABLE shop.users ALTER COLUMN email SET NOT NULL")
    op.execute("ALTER TABLE shop.users ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0")
    op.execute(
        "CREATE TABLE IF NOT EXISTS shop.password_reset_tokens ("
        "id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES shop.users(id), "
        "token_hash VARCHAR NOT NULL UNIQUE, expires_at TIMESTAMP WITH TIME ZONE NOT NULL, "
        "used_at TIMESTAMP WITH TIME ZONE, created_at TIMESTAMP WITH TIME ZONE NOT NULL)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_shop_users_email ON shop.users (email)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_shop_password_reset_tokens_user_id ON shop.password_reset_tokens (user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS shop.password_reset_tokens")
    op.execute("ALTER TABLE shop.users DROP COLUMN IF EXISTS token_version")
    op.execute("ALTER TABLE shop.users DROP COLUMN IF EXISTS email")
