from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class ProductStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SOLD = "SOLD"


class ProductCategory(str, enum.Enum):
    SHOES = "SHOES"
    CLOTHING = "CLOTHING"
    ACCESSORIES = "ACCESSORIES"

    @property
    def label(self) -> str:
        return {
            ProductCategory.SHOES: "Обувь",
            ProductCategory.CLOTHING: "Одежда",
            ProductCategory.ACCESSORIES: "Аксессуары",
        }[self]

    @classmethod
    def from_label(cls, label: str) -> "ProductCategory":
        normalized = label.strip().lower()
        mapping = {
            "обувь": cls.SHOES,
            "одежда": cls.CLOTHING,
            "аксессуары": cls.ACCESSORIES,
        }
        return mapping[normalized]


class ProductSource(str, enum.Enum):
    BOT = "BOT"
    CHANNEL_IMPORT = "CHANNEL_IMPORT"


class OrderContactMethod(str, enum.Enum):
    TELEGRAM = "TELEGRAM"
    PHONE = "PHONE"
    WHATSAPP = "WHATSAPP"


class DeliveryProvider(str, enum.Enum):
    CDEK = "CDEK"
    OZON = "OZON"
    YANDEX = "YANDEX"


class PaymentMethod(str, enum.Enum):
    CARD = "CARD"
    CRYPTO = "CRYPTO"
    PHONE_NUMBER = "PHONE_NUMBER"


class CryptoNetwork(str, enum.Enum):
    BEP20 = "BEP20"
    TRC20 = "TRC20"
    TON = "TON"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    size: Mapped[str] = mapped_column(String(100), nullable=False)
    condition: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[ProductCategory] = mapped_column(
        Enum(ProductCategory, name="product_category"),
        nullable=False,
    )
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    old_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus, name="product_status"),
        default=ProductStatus.ACTIVE,
        server_default=ProductStatus.ACTIVE.value,
        nullable=False,
        index=True,
    )
    channel_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    channel_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    channel_media_group_message_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger),
        nullable=True,
    )
    source: Mapped[ProductSource] = mapped_column(
        Enum(ProductSource, name="product_source"),
        default=ProductSource.BOT,
        server_default=ProductSource.BOT.value,
        nullable=False,
    )
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    entities_json: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    caption_entities_json: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    html_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    html_caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    photos: Mapped[list["ProductPhoto"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductPhoto.sort_order",
    )
    order_items: Mapped[list["OrderItem"]] = relationship(back_populates="product")


class ProductPhoto(Base):
    __tablename__ = "product_photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    file_id: Mapped[str] = mapped_column(String(1024), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)

    product: Mapped[Product] = relationship(back_populates="photos")


class AdminActionLog(Base):
    __tablename__ = "admin_action_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class StoreSettings(Base):
    __tablename__ = "store_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    background_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#505559", server_default="#505559")
    avatar_file_id: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    cover_file_id: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telegram_first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_username: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_method: Mapped[OrderContactMethod] = mapped_column(
        Enum(OrderContactMethod, name="order_contact_method"),
        nullable=False,
    )
    delivery_provider: Mapped[DeliveryProvider | None] = mapped_column(
        Enum(DeliveryProvider, name="delivery_provider"), nullable=True
    )
    delivery_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        Enum(PaymentMethod, name="payment_method"), nullable=True
    )
    crypto_network: Mapped[CryptoNetwork | None] = mapped_column(
        Enum(CryptoNetwork, name="crypto_network"), nullable=True
    )
    total_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderItem.id",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    product_title: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped[Product | None] = relationship(back_populates="order_items")
