from app.database.models import Product, ProductCategory, ProductPhoto, ProductStatus
from app.services import formatter
from app.utils import premium_emoji as emoji


def build_product(**overrides) -> Product:
    product = Product(
        id=1,
        title=overrides.get("title", 'Stone <Island> "Ghost"'),
        size=overrides.get("size", "M"),
        condition=overrides.get("condition", "Новые 10/10"),
        description=overrides.get("description", "0"),
        category=overrides.get("category", ProductCategory.CLOTHING),
        price=overrides.get("price", 17990),
        old_price=overrides.get("old_price"),
        status=overrides.get("status", ProductStatus.ACTIVE),
    )
    product.photos = [ProductPhoto(file_id="file-1", sort_order=1)]
    return product


def test_format_start_message_contains_html_link_and_premium_emoji() -> None:
    text = formatter.format_start_message("Timur", "https://example.com/tiktok")
    assert "Привет, Timur" in text
    assert '<a href="https://example.com/tiktok">ТИК ТОК</a>' in text
    assert emoji.SHOP in text


def test_format_product_card_hides_zero_description_and_escapes_html() -> None:
    product = build_product(old_price=21990)
    text = formatter.format_product_card(product, "demo_support")
    assert "Описание:" not in text
    assert "Stone &lt;Island&gt; &quot;Ghost&quot;" in text
    assert "<s>21990 ₽</s> 17990 ₽" in text
    assert "@demo_support" in text


def test_format_sold_post_uses_final_price_without_old_price_markup() -> None:
    product = build_product(old_price=21990, status=ProductStatus.SOLD, price=19990, description="Редкий товар")
    text = formatter.format_sold_post(product, "demo_support")
    assert emoji.CROSS in text
    assert "<s>21990 ₽</s>" not in text
    assert "Цена: <b>19990 ₽</b>" in text
    assert "Описание:" not in text
    assert "Редкий товар" in text


def test_format_channel_post_matches_store_style() -> None:
    product = build_product(
        title="Stone Island Hand Sprayed",
        size="S",
        condition="Полностью Новый 10/10 с навесными",
        description="Единственный экземпляр в Рф",
        price=34990,
    )
    text = formatter.format_channel_post(product, "demo_support")
    assert text.startswith(f"<b>{emoji.CHECK} В НАЛИЧИИ {emoji.CHECK}</b>")
    assert "🏷" not in text
    assert "Размер: <b>S</b>" in text
    assert "Единственный экземпляр в Рф" in text
    assert "Цена: <b>34990 ₽</b>" in text
    assert "<b>#вналичии</b>" in text
    assert '<a href="https://t.me/demo_support">@demo_support</a>' in text
