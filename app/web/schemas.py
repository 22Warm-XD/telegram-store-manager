from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.database.models import CryptoNetwork, DeliveryProvider, OrderContactMethod, PaymentMethod, ProductCategory, ProductStatus


class CategoryResponse(BaseModel):
    key: ProductCategory
    label: str


class StoreMetaResponse(BaseModel):
    shop_name: str
    support_url: str
    reviews_url: str
    tiktok_url: str
    mini_app_url: str | None
    background_color: str
    avatar_url: str | None
    cover_url: str | None
    payment_options: "PaymentOptionsResponse"


class PaymentOptionsResponse(BaseModel):
    card_available: bool
    card_number: str | None = None
    card_holder: str | None = None
    phone_available: bool
    phone_number: str | None = None
    phone_holder: str | None = None
    crypto_networks: dict[CryptoNetwork, str]


class ProductResponse(BaseModel):
    id: int
    title: str
    price: int
    old_price: int | None
    category: ProductCategory
    category_label: str
    size: str
    condition: str
    description: str | None
    status: ProductStatus
    status_label: str
    photos: list[str]
    photo_count: int
    created_at: datetime
    is_new: bool
    is_favorite_available: bool = True


class WebAppValidateRequest(BaseModel):
    init_data: str = Field(min_length=1)


class WebAppUserResponse(BaseModel):
    id: int
    first_name: str | None = None
    username: str | None = None
    last_name: str | None = None


class WebAppValidateResponse(BaseModel):
    ok: bool
    user: WebAppUserResponse


class OrderItemRequest(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=1)


class OrderCreateRequest(BaseModel):
    init_data: str | None = Field(default=None)
    name: str = Field(min_length=1, max_length=255)
    username: str = Field(min_length=2, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    comment: str | None = Field(default=None, max_length=2000)
    contact_method: OrderContactMethod
    delivery_provider: DeliveryProvider
    delivery_address: str = Field(min_length=1, max_length=500)
    payment_method: PaymentMethod
    crypto_network: CryptoNetwork | None = None
    items: list[OrderItemRequest]

    @field_validator("items")
    @classmethod
    def validate_items(cls, value: list[OrderItemRequest]) -> list[OrderItemRequest]:
        if not value:
            raise ValueError("Корзина пуста.")
        return value

    @model_validator(mode="after")
    def validate_contact_details(self) -> "OrderCreateRequest":
        if not self.delivery_address.strip():
            raise ValueError("Delivery address is required.")
        if self.payment_method == PaymentMethod.CRYPTO and self.crypto_network is None:
            raise ValueError("Crypto network is required.")
        if self.payment_method != PaymentMethod.CRYPTO and self.crypto_network is not None:
            raise ValueError("Crypto network is only valid for crypto payments.")
        if self.contact_method in {OrderContactMethod.PHONE, OrderContactMethod.WHATSAPP}:
            if not self.phone or not self.phone.strip():
                raise ValueError("Для выбранного способа связи нужно указать телефон.")
        return self


class OrderCreateResponse(BaseModel):
    ok: bool
    order_id: int
    total_amount: int
    message: str
