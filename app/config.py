from __future__ import annotations

from typing import Annotated
from functools import cached_property

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    bot_token: str = Field(alias="BOT_TOKEN")
    admin_ids: Annotated[set[int], NoDecode] = Field(alias="ADMIN_IDS")
    channel_id: int = Field(alias="CHANNEL_ID")

    support_username: str = Field(alias="SUPPORT_USERNAME")
    support_url: str = Field(alias="SUPPORT_URL")
    reviews_url: str = Field(alias="REVIEWS_URL")
    tiktok_url: str = Field(alias="TIKTOK_URL")
    logistics_url: str = Field(alias="LOGISTICS_URL")
    mini_app_url: str | None = Field(default=None, alias="MINI_APP_URL")
    caddy_site_address: str | None = Field(default=None, alias="CADDY_SITE_ADDRESS")

    payment_card_number: str = Field(default="", alias="PAYMENT_CARD_NUMBER")
    payment_card_holder: str = Field(default="", alias="PAYMENT_CARD_HOLDER")
    payment_phone_number: str = Field(default="", alias="PAYMENT_PHONE_NUMBER")
    payment_phone_holder: str = Field(default="", alias="PAYMENT_PHONE_HOLDER")
    payment_crypto_bep20: str = Field(default="", alias="PAYMENT_CRYPTO_BEP20")
    payment_crypto_trc20: str = Field(default="", alias="PAYMENT_CRYPTO_TRC20")
    payment_crypto_ton: str = Field(default="", alias="PAYMENT_CRYPTO_TON")

    postgres_host: str = Field(alias="POSTGRES_HOST")
    postgres_port: int = Field(alias="POSTGRES_PORT")
    postgres_db: str = Field(alias="POSTGRES_DB")
    postgres_user: str = Field(alias="POSTGRES_USER")
    postgres_password: str = Field(alias="POSTGRES_PASSWORD")

    redis_host: str = Field(alias="REDIS_HOST")
    redis_port: int = Field(alias="REDIS_PORT")
    redis_db: int = Field(alias="REDIS_DB")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, value: str | set[int] | list[int]) -> set[int]:
        if isinstance(value, set):
            return value
        if isinstance(value, list):
            return {int(item) for item in value}
        return {int(item.strip()) for item in str(value).split(",") if item.strip()}

    @cached_property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @cached_property
    def redis_dsn(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


def load_settings() -> Settings:
    return Settings()
