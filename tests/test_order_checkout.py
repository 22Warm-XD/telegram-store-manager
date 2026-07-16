from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.database.models import CryptoNetwork, DeliveryProvider, PaymentMethod
from app.web.schemas import OrderCreateRequest


def payload(**overrides):
    value = {
        "name": "Buyer",
        "username": "buyer",
        "contact_method": "TELEGRAM",
        "delivery_provider": "CDEK",
        "delivery_address": "Набережные Челны, проспект Мира, 1",
        "payment_method": "CARD",
        "crypto_network": None,
        "items": [{"product_id": 1, "quantity": 1}],
    }
    value.update(overrides)
    return OrderCreateRequest(**value)


def test_orders_accept_configured_delivery_and_payment_variants() -> None:
    assert payload().delivery_provider == DeliveryProvider.CDEK
    assert payload(delivery_provider="OZON", payment_method="CRYPTO", crypto_network="BEP20").crypto_network == CryptoNetwork.BEP20
    assert payload(delivery_provider="YANDEX", payment_method="CRYPTO", crypto_network="TON").payment_method == PaymentMethod.CRYPTO


@pytest.mark.parametrize(
    "changes",
    [
        {"delivery_address": "   "},
        {"delivery_provider": "UNKNOWN"},
        {"payment_method": "CRYPTO", "crypto_network": None},
        {"payment_method": "CRYPTO", "crypto_network": "UNKNOWN"},
        {"payment_method": "CARD", "crypto_network": "TON"},
    ],
)
def test_orders_reject_invalid_delivery_or_crypto(changes) -> None:
    with pytest.raises(ValidationError):
        payload(**changes)
