from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from urllib.parse import urlencode

import pytest

from app.web.auth import WebAppAuthError, validate_init_data


def _build_init_data(*, bot_token: str, user: dict, auth_date: int | None = None) -> str:
    payload = {
        "auth_date": str(auth_date or int(datetime.now(tz=UTC).timestamp())),
        "query_id": "AAEAAAE",
        "user": json.dumps(user, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(payload.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    payload["hash"] = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return urlencode(payload)


def test_validate_init_data_success() -> None:
    init_data = _build_init_data(
        bot_token="123:test-token",
        user={"id": 12345, "first_name": "Demo", "username": "store_user"},
    )

    auth = validate_init_data(init_data, bot_token="123:test-token")

    assert auth.user.id == 12345
    assert auth.user.first_name == "Demo"
    assert auth.user.username == "store_user"


def test_validate_init_data_rejects_invalid_hash() -> None:
    init_data = _build_init_data(
        bot_token="123:test-token",
        user={"id": 12345, "first_name": "Timur"},
    )
    invalid_init_data = init_data.replace("hash=", "hash=broken")

    with pytest.raises(WebAppAuthError):
        validate_init_data(invalid_init_data, bot_token="123:test-token")
