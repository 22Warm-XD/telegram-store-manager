from app.utils.pricing import parse_price


def test_parse_price_accepts_common_thousands_separators() -> None:
    assert parse_price("35000") == 35000
    assert parse_price("35 000 ₽") == 35000
    assert parse_price("35.000") == 35000
    assert parse_price("35,000 руб.") == 35000


def test_parse_price_rejects_invalid_values() -> None:
    assert parse_price("") is None
    assert parse_price("цена договорная") is None
    assert parse_price("0") is None
