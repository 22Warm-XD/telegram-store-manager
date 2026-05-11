from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260424_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    product_category = postgresql.ENUM(
        "SHOES",
        "CLOTHING",
        "ACCESSORIES",
        name="product_category",
        create_type=False,
    )
    product_status = postgresql.ENUM(
        "ACTIVE",
        "SOLD",
        name="product_status",
        create_type=False,
    )
    product_category.create(op.get_bind(), checkfirst=True)
    product_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("size", sa.String(length=100), nullable=False),
        sa.Column("condition", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", product_category, nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("old_price", sa.Integer(), nullable=True),
        sa.Column("status", product_status, server_default="ACTIVE", nullable=False),
        sa.Column("channel_message_id", sa.BigInteger(), nullable=True),
        sa.Column("channel_media_group_message_ids", postgresql.ARRAY(sa.BigInteger()), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_products_status", "products", ["status"], unique=False)

    op.create_table(
        "product_photos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_id", sa.String(length=1024), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
    )

    op.create_table(
        "admin_action_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("admin_id", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_admin_action_logs_admin_id", "admin_action_logs", ["admin_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_admin_action_logs_admin_id", table_name="admin_action_logs")
    op.drop_table("admin_action_logs")
    op.drop_table("product_photos")
    op.drop_index("ix_products_status", table_name="products")
    op.drop_table("products")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_table("users")

    sa.Enum(name="product_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="product_category").drop(op.get_bind(), checkfirst=True)
