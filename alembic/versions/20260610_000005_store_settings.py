"""add store settings

Revision ID: 20260610_000005
Revises: 20260428_000004
Create Date: 2026-06-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260610_000005"
down_revision: Union[str, None] = "20260428_000004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "store_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("background_color", sa.String(length=7), server_default="#505559", nullable=False),
        sa.Column("avatar_file_id", sa.String(length=1024), nullable=True),
        sa.Column("cover_file_id", sa.String(length=1024), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.execute("INSERT INTO store_settings (id, background_color) VALUES (1, '#505559')")


def downgrade() -> None:
    op.drop_table("store_settings")
