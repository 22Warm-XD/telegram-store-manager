"""add delivery and payment details to orders

Revision ID: 20260716_000006
Revises: 20260610_000005
"""

from alembic import op
import sqlalchemy as sa

revision = "20260716_000006"
down_revision = "20260610_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    delivery_provider = sa.Enum("CDEK", "OZON", "YANDEX", name="delivery_provider")
    payment_method = sa.Enum("CARD", "CRYPTO", "PHONE_NUMBER", name="payment_method")
    crypto_network = sa.Enum("BEP20", "TRC20", "TON", name="crypto_network")
    delivery_provider.create(op.get_bind(), checkfirst=True)
    payment_method.create(op.get_bind(), checkfirst=True)
    crypto_network.create(op.get_bind(), checkfirst=True)
    op.add_column("orders", sa.Column("delivery_provider", delivery_provider, nullable=True))
    op.add_column("orders", sa.Column("delivery_address", sa.String(length=500), nullable=True))
    op.add_column("orders", sa.Column("payment_method", payment_method, nullable=True))
    op.add_column("orders", sa.Column("crypto_network", crypto_network, nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "crypto_network")
    op.drop_column("orders", "payment_method")
    op.drop_column("orders", "delivery_address")
    op.drop_column("orders", "delivery_provider")
    sa.Enum(name="crypto_network").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="payment_method").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="delivery_provider").drop(op.get_bind(), checkfirst=True)
