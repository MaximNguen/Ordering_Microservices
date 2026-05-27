"""remove products table from orders service

Revision ID: b7f1a2c3d4e5
Revises: 2f72925c6c7b
Create Date: 2026-05-27 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7f1a2c3d4e5"
down_revision: Union[str, Sequence[str], None] = "2f72925c6c7b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE order_items DROP CONSTRAINT IF EXISTS order_items_product_id_fkey")
    op.drop_table("products")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        "products",
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("price", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("product_id"),
    )
    op.create_foreign_key(
        "order_items_product_id_fkey",
        "order_items",
        "products",
        ["product_id"],
        ["product_id"],
    )
