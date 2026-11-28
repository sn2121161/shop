"""Assign each data consulting product its own cover."""

import sqlalchemy as sa
from alembic import op

revision = "20261128_06"
down_revision = "20261128_05"
branch_labels = None
depends_on = None

PREVIOUS_COVER = "/images/data-consulting.webp"
COVERS = {
    "网页爬虫与数据采集服务": "/images/data-collection-cover.webp",
    "定制化数据咨询服务": "/images/data-visualization-cover.webp",
    "全流程数据服务与年度运维": "/images/data-research-cover.webp",
}
PRODUCTS = sa.table("products", sa.column("name"), sa.column("image_path"), schema="shop")


def upgrade():
    for name, path in COVERS.items():
        op.execute(PRODUCTS.update().where(PRODUCTS.c.name == name).values(image_path=path))


def downgrade():
    for name, path in COVERS.items():
        op.execute(PRODUCTS.update().where(
            PRODUCTS.c.name == name, PRODUCTS.c.image_path == path,
        ).values(image_path=PREVIOUS_COVER))
