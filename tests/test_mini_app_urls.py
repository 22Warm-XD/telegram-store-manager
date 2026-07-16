from app.database.models import ProductCategory
from app.keyboards.catalog import product_detail_keyboard
from app.keyboards.user import main_menu_inline_keyboard
from app.utils.mini_app import build_mini_app_url


def test_build_mini_app_url_for_base_url() -> None:
    assert build_mini_app_url("https://domain.example/app", "abc123") == "https://domain.example/app?v=abc123"


def test_build_mini_app_url_preserves_existing_query() -> None:
    assert (
        build_mini_app_url("https://domain.example/app?source=telegram", "abc123")
        == "https://domain.example/app?v=abc123&source=telegram"
    )


def test_build_mini_app_url_replaces_version_and_sets_product() -> None:
    assert (
        build_mini_app_url("https://domain.example/app?product=12&v=old", "abc123", product_id=42)
        == "https://domain.example/app?v=abc123&product=42"
    )


def test_build_mini_app_url_rejects_non_https_url() -> None:
    assert build_mini_app_url("http://domain.example/app", "abc123") is None


def test_native_catalog_order_button_uses_versioned_product_url() -> None:
    keyboard = product_detail_keyboard(
        support_url="https://t.me/support",
        mini_app_url="https://domain.example/app?source=catalog",
        app_version="abc123",
        product_id=15,
        category=ProductCategory.CLOTHING,
        page=1,
    )
    order_button = keyboard.inline_keyboard[0][0]

    assert order_button.text == "Заказать"
    assert order_button.web_app is not None
    assert order_button.web_app.url == "https://domain.example/app?v=abc123&source=catalog&product=15"


def test_main_menu_uses_versioned_web_app_url() -> None:
    keyboard = main_menu_inline_keyboard(
        reviews_url="https://t.me/reviews",
        support_url="https://t.me/support",
        mini_app_url="https://domain.example/app",
        app_version="abc123",
    )
    store_button = keyboard.inline_keyboard[0][0]

    assert store_button.web_app is not None
    assert store_button.web_app.url == "https://domain.example/app?v=abc123"
