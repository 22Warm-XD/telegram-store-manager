from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260426_000002"
down_revision = "20260424_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    product_source = postgresql.ENUM("BOT", "CHANNEL_IMPORT", name="product_source", create_type=False)
    product_source.create(op.get_bind(), checkfirst=True)

    op.add_column("products", sa.Column("channel_chat_id", sa.BigInteger(), nullable=True))
    op.add_column(
        "products",
        sa.Column(
            "source",
            product_source,
            server_default="BOT",
            nullable=False,
        ),
    )
    op.add_column("products", sa.Column("raw_text", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("raw_caption", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("entities_json", postgresql.JSONB(), nullable=True))
    op.add_column("products", sa.Column("caption_entities_json", postgresql.JSONB(), nullable=True))
    op.add_column("products", sa.Column("html_text", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("html_caption", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "html_caption")
    op.drop_column("products", "html_text")
    op.drop_column("products", "caption_entities_json")
    op.drop_column("products", "entities_json")
    op.drop_column("products", "raw_caption")
    op.drop_column("products", "raw_text")
    op.drop_column("products", "source")
    op.drop_column("products", "channel_chat_id")
    sa.Enum(name="product_source").drop(op.get_bind(), checkfirst=True)
