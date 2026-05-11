from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260428_000004"
down_revision = "20260428_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("contact_username", sa.String(length=255), nullable=True))
    op.execute("UPDATE orders SET contact_username = COALESCE(telegram_username, '@unknown') WHERE contact_username IS NULL")
    op.alter_column("orders", "contact_username", existing_type=sa.String(length=255), nullable=False)
    op.alter_column("orders", "phone", existing_type=sa.String(length=50), nullable=True)


def downgrade() -> None:
    op.alter_column("orders", "phone", existing_type=sa.String(length=50), nullable=False)
    op.drop_column("orders", "contact_username")
