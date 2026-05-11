from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import parse_qsl


class WebAppAuthError(Exception):
    """Raised when Telegram WebApp initData is invalid."""


@dataclass(slots=True)
class TelegramWebAppUser:
    id: int
    first_name: str | None = None
    username: str | None = None
    last_name: str | None = None


@dataclass(slots=True)
class TelegramWebAppAuth:
    user: TelegramWebAppUser
    auth_date: datetime
    query_id: str | None = None


def validate_init_data(
    init_data: str,
    *,
    bot_token: str,
    max_age_seconds: int = 86400,
) -> TelegramWebAppAuth:
    if not init_data.strip():
        raise WebAppAuthError("Пустой initData.")

    values = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = values.pop("hash", None)
    if not received_hash:
        raise WebAppAuthError("В initData отсутствует hash.")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise WebAppAuthError("initData signature mismatch.")

    auth_date_raw = values.get("auth_date")
    if auth_date_raw is None:
        raise WebAppAuthError("В initData отсутствует auth_date.")
    auth_date = datetime.fromtimestamp(int(auth_date_raw), tz=UTC)
    age_seconds = (datetime.now(tz=UTC) - auth_date).total_seconds()
    if age_seconds > max_age_seconds:
        raise WebAppAuthError("initData устарел.")

    user_raw = values.get("user")
    if not user_raw:
        raise WebAppAuthError("В initData отсутствует пользователь.")
    user_payload = json.loads(user_raw)
    user = TelegramWebAppUser(
        id=int(user_payload["id"]),
        first_name=user_payload.get("first_name"),
        username=user_payload.get("username"),
        last_name=user_payload.get("last_name"),
    )
    return TelegramWebAppAuth(
        user=user,
        auth_date=auth_date,
        query_id=values.get("query_id"),
    )
