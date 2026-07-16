from __future__ import annotations

from dataclasses import dataclass
from html import escape

from aiogram.types import MessageEntity

from app.database.models import Product, ProductCategory, ProductSource, ProductStatus
from app.utils import premium_emoji as emoji


@dataclass(slots=True)
class FormattedTelegramText:
    text: str
    entities: list[MessageEntity]


def _clean_description(description: str | None) -> str | None:
    if description is None:
        return None
    cleaned = description.strip()
    if not cleaned or cleaned == "0":
        return None
    return cleaned


def _safe_username(username: str) -> str:
    normalized = username.strip()
    return normalized if normalized.startswith("@") else f"@{normalized}"


def _price_line(product: Product, *, allow_discount_markup: bool = True) -> str:
    if allow_discount_markup and product.status == ProductStatus.ACTIVE and product.old_price:
        return f"Цена: <s>{product.old_price} ₽</s> {product.price} ₽"
    return f"Цена: {product.price} ₽"


def _channel_price_line(product: Product) -> str:
    if product.status == ProductStatus.ACTIVE and product.old_price:
        return f"Цена: <b><s>{product.old_price} ₽</s> {product.price} ₽</b>"
    return f"Цена: <b>{product.price} ₽</b>"


def _channel_price_text(product: Product) -> str:
    if product.status == ProductStatus.ACTIVE and product.old_price:
        return f"Цена {product.old_price} {product.price}"
    return f"Цена {product.price}"


def _render_description_block(description: str | None, *, with_label: bool = True) -> str:
    cleaned = _clean_description(description)
    if not cleaned:
        return ""
    label = "Описание: " if with_label else ""
    return f"\n{label}{escape(cleaned)}"


def _render_plain_description_block(description: str | None) -> str:
    cleaned = _clean_description(description)
    if not cleaned:
        return ""
    return f"\n{cleaned}"


def _render_channel_description_block(description: str | None) -> str:
    cleaned = _clean_description(description)
    if not cleaned:
        return ""
    return escape(cleaned)


def _admin_link(username: str) -> str:
    safe_username = escape(_safe_username(username))
    clean_username = safe_username.lstrip("@")
    return f'<a href="https://t.me/{clean_username}">{safe_username}</a>'


def _utf16_len(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def _utf16_offset(value: str, index: int) -> int:
    return _utf16_len(value[:index])


def _entity_span(text: str, needle: str, *, start: int = 0) -> tuple[int, int, int]:
    index = text.find(needle, start)
    if index < 0:
        raise ValueError(f"Cannot find entity text: {needle!r}")
    return index, _utf16_offset(text, index), _utf16_len(needle)


def _custom_emoji_entity(text: str, fallback: str, emoji_id: str, *, start: int = 0) -> MessageEntity:
    index, offset, length = _entity_span(text, fallback, start=start)
    return MessageEntity(type="custom_emoji", offset=offset, length=length, custom_emoji_id=emoji_id)


def _channel_admin_username(support_username: str) -> str:
    return _safe_username(support_username)


def _channel_admin_url(support_username: str) -> str:
    return f"https://t.me/{_safe_username(support_username).lstrip('@')}"


def format_start_message(name: str, tiktok_url: str) -> str:
    safe_name = escape(name or "друг")
    return (
        f"Привет, {safe_name} 👋\n\n"
        f"Вас приветствует чат-бот магазина Kuznetsky Store {emoji.SHOP}\n\n"
        f"{emoji.WARNING} Строго оригинальные позиции\n"
        f"{emoji.WARNING} Личная встреча в г. Стерлитамак\n"
        f"{emoji.WARNING} Отправка в разные регионы: Авито, СДЭК, Яндекс, Почта России\n\n"
        "Чтобы оформить заказ, перейдите в «Каталог», выберите товар и напишите менеджеру.\n\n"
        "🔗 Наши соцсети:\n"
        f'<a href="{escape(tiktok_url, quote=True)}">ТИК ТОК</a>\n\n'
        "Задать вопрос можно через кнопку «Поддержка»."
    )


def format_support_message(*, title: str, body: str) -> str:
    return f"{title}\n\n{body}"


def format_empty_category_message() -> str:
    return "В этой категории пока нет товаров."


def format_no_access_message() -> str:
    return "У вас нет доступа к админ-панели."


def format_admin_menu_message() -> str:
    return (
        f"{emoji.SHOP} <b>Kuznetsky Store Admin</b>\n\n"
        "Управляйте объявлениями, скидками и статусами товаров."
    )


def format_channel_post(product: Product, support_username: str) -> str:
    title = escape(product.title)
    size = escape(product.size)
    condition = escape(product.condition)
    description_block = _render_channel_description_block(product.description)
    return (
        f"<b>{emoji.CHECK} В НАЛИЧИИ {emoji.CHECK}</b>\n\n"
        f"<b>{title}</b>\n\n"
        f"Размер: <b>{size}</b>\n\n"
        f"Состояние: <b>{condition}</b>"
        f"{f'\n\n<b>{description_block}</b>' if description_block else ''}\n\n"
        f"{_channel_price_line(product)}\n\n"
        "<b>#вналичии</b>\n\n"
        f"Админ: <b>{_admin_link(support_username)}</b>"
    )


def format_channel_post_entities(product: Product, support_username: str) -> FormattedTelegramText:
    title = product.title
    size = product.size
    condition = product.condition
    description_block = _render_plain_description_block(product.description)
    admin_username = _channel_admin_username(support_username)
    text = (
        f"{emoji.CHECK_PLAIN}В НАЛИЧИИ{emoji.CHECK_PLAIN}\n\n"
        f"{title}\n\n"
        f"Размер {size}\n\n"
        f"Состояние: {condition}"
        f"{description_block}\n\n"
        f"{_channel_price_text(product)}\n\n"
        "#вналичии\n\n"
        f"Админ {admin_username}"
    )

    entities = _base_channel_entities(text, admin_username, _channel_admin_url(support_username))
    _add_price_strike_entity(text, entities, product)
    return FormattedTelegramText(text=text, entities=entities)


def format_discount_post(product: Product, support_username: str) -> str:
    title = escape(product.title)
    size = escape(product.size)
    condition = escape(product.condition)
    admin_username = escape(_safe_username(support_username))
    old_price = product.old_price if product.old_price is not None else product.price
    return (
        f"{emoji.FIRE} СКИДКА {emoji.FIRE}\n\n"
        f"<b>{title}</b>\n\n"
        f"Старая цена: <s>{old_price} ₽</s>\n"
        f"Новая цена: {product.price} ₽\n\n"
        f"Размер: {size}\n"
        f"Состояние: {condition}\n\n"
        "#скидка\n\n"
        f"{emoji.USER} Админ {admin_username}"
    )


def format_sold_post(product: Product, support_username: str) -> str:
    title = escape(product.title)
    size = escape(product.size)
    condition = escape(product.condition)
    description_block = _render_channel_description_block(product.description)
    return (
        f"<b>{emoji.CROSS} SOLD {emoji.CROSS}</b>\n\n"
        f"<b>{title}</b>\n\n"
        f"Размер: <b>{size}</b>\n\n"
        f"Состояние: <b>{condition}</b>"
        f"{f'\n\n<b>{description_block}</b>' if description_block else ''}\n\n"
        f"Цена: <b>{product.price} ₽</b>\n\n"
        "<b>#sold</b>\n\n"
        f"Админ: <b>{_admin_link(support_username)}</b>"
    )


def format_sold_post_entities(product: Product, support_username: str) -> FormattedTelegramText:
    title = product.title
    size = product.size
    condition = product.condition
    description_block = _render_description_block(product.description, with_label=False)
    admin_username = _channel_admin_username(support_username)
    text = (
        f"{emoji.CROSS_PLAIN}SOLD{emoji.CROSS_PLAIN}\n\n"
        f"{title}\n\n"
        f"Размер {size}\n\n"
        f"Состояние: {condition}"
        f"{description_block}\n\n"
        f"Цена {product.price}\n\n"
        "#sold\n\n"
        f"Админ {admin_username}"
    )

    entities = _base_channel_entities(text, admin_username, _channel_admin_url(support_username))
    first_cross_index = text.find(emoji.CROSS_PLAIN)
    second_cross_start = first_cross_index + len(emoji.CROSS_PLAIN)
    entities.append(_custom_emoji_entity(text, emoji.CROSS_PLAIN, emoji.CROSS_ID))
    entities.append(_custom_emoji_entity(text, emoji.CROSS_PLAIN, emoji.CROSS_ID, start=second_cross_start))
    return FormattedTelegramText(text=text, entities=entities)


def _base_channel_entities(text: str, admin_username: str, admin_url: str) -> list[MessageEntity]:
    entities: list[MessageEntity] = [
        MessageEntity(type="bold", offset=0, length=_utf16_len(text)),
    ]
    admin_index, admin_offset, admin_length = _entity_span(text, admin_username)
    entities.append(
        MessageEntity(
            type="text_link",
            offset=admin_offset,
            length=admin_length,
            url=admin_url,
        )
    )
    first_check_index = text.find(emoji.CHECK_PLAIN)
    if first_check_index >= 0:
        second_check_start = first_check_index + len(emoji.CHECK_PLAIN)
        entities.append(_custom_emoji_entity(text, emoji.CHECK_PLAIN, emoji.CHECK_ID))
        entities.append(_custom_emoji_entity(text, emoji.CHECK_PLAIN, emoji.CHECK_ID, start=second_check_start))
    return entities


def _add_price_strike_entity(text: str, entities: list[MessageEntity], product: Product) -> None:
    if product.status != ProductStatus.ACTIVE or not product.old_price:
        return
    old_price = str(product.old_price)
    _, offset, length = _entity_span(text, old_price)
    entities.append(MessageEntity(type="strikethrough", offset=offset, length=length))


def format_product_card(product: Product, support_username: str) -> str:
    if (
        product.source == ProductSource.CHANNEL_IMPORT
        and product.status == ProductStatus.ACTIVE
        and product.old_price is None
        and (product.html_caption or product.html_text)
    ):
        return product.html_caption or product.html_text or ""

    title = escape(product.title)
    size = escape(product.size)
    condition = escape(product.condition)
    description_block = _render_description_block(product.description)
    admin_username = escape(_safe_username(support_username))
    status_line = f"{emoji.CHECK} В наличии" if product.status == ProductStatus.ACTIVE else f"{emoji.CROSS} Продано"
    return (
        f"{status_line}\n\n"
        f"{emoji.TAG} <b>{title}</b>\n\n"
        f"Размер: {size}\n"
        f"Состояние: {condition}"
        f"{description_block}\n"
        f"{_price_line(product)}\n\n"
        f"{emoji.USER} Менеджер {admin_username}"
    )


def format_admin_product_card(product: Product, support_username: str) -> str:
    category = product.category.label
    status_label = "В наличии" if product.status == ProductStatus.ACTIVE else "Продан"
    return (
        f"{format_product_card(product, support_username)}\n\n"
        f"Категория: {escape(category)}\n"
        f"Статус: {escape(status_label)}"
    )


def format_admin_preview(product: Product, support_username: str) -> str:
    return (
        f"{emoji.PHOTO} <b>Предпросмотр товара</b>\n\n"
        f"{format_admin_product_card(product, support_username)}"
    )


def format_photo_prompt() -> str:
    return (
        f"{emoji.PHOTO} Скиньте фото товара.\n\n"
        "Можно отправить от 1 до 5 фотографий. После первой фотографии станет доступна кнопка «Готово»."
    )


def format_photo_saved_message(total: int) -> str:
    return f"{emoji.CHECK} Фото сохранено. Сейчас в черновике: {total}/5."


def format_photo_limit_message() -> str:
    return f"{emoji.EXCLAMATION} Максимум можно добавить 5 фото."


def format_enter_title_prompt() -> str:
    return f"{emoji.TAG} Введите название товара."


def format_enter_size_prompt() -> str:
    return "Введите размер товара."


def format_enter_price_prompt() -> str:
    return "Введите цену товара."


def format_invalid_price_message() -> str:
    return f"{emoji.EXCLAMATION} Цена должна быть числом. Введите цену заново."


def format_enter_condition_prompt() -> str:
    return "Введите состояние товара."


def format_enter_description_prompt() -> str:
    return "Введите описание товара.\nЕсли описание не нужно, отправьте 0."


def format_choose_category_prompt() -> str:
    return "Выберите категорию товара:"


def format_invalid_category_message() -> str:
    return f"{emoji.EXCLAMATION} Категорию нужно выбрать кнопкой."


def format_product_published_message() -> str:
    return f"{emoji.CHECK} Товар опубликован."


def format_channel_error_message() -> str:
    return (
        f"{emoji.EXCLAMATION} Не удалось опубликовать товар в канал.\n"
        "Проверьте, что бот добавлен в канал и имеет права администратора."
    )


def format_product_not_found_message() -> str:
    return f"{emoji.EXCLAMATION} Товар не найден."


def format_unknown_message() -> str:
    return f"{emoji.WARNING} Я не понял сообщение. Выберите действие по кнопкам ниже."


def format_discount_prompt() -> str:
    return "Введите новую цену товара."


def format_discount_success_message() -> str:
    return f"{emoji.FIRE} Скидка применена."


def format_discount_removed_message() -> str:
    return f"{emoji.CHECK} Скидка удалена."


def format_discount_blocked_message() -> str:
    return f"{emoji.EXCLAMATION} Если товар уже продан, нельзя сделать скидку."


def format_discount_must_be_lower_message() -> str:
    return f"{emoji.EXCLAMATION} Новая цена должна быть меньше текущей."


def format_sold_success_message() -> str:
    return f"{emoji.CROSS} Товар отмечен как проданный."


def format_archive_success_message() -> str:
    return f"{emoji.CHECK} Товар скрыт из списка проданных."


def format_cancelled_message() -> str:
    return f"{emoji.CROSS} Действие отменено."


def format_reviews_message() -> str:
    return f"{emoji.SHIELD} Отзывы Kuznetsky Store\n\nОткройте отзывы по кнопке ниже."


def format_support_link_message() -> str:
    return f"{emoji.USER} Поддержка Kuznetsky Store\n\nНапишите менеджеру по кнопке ниже."


def format_catalog_message() -> str:
    return f"{emoji.SHOP} Выберите категорию товара."


def format_empty_list_message(status: ProductStatus) -> str:
    if status == ProductStatus.ACTIVE:
        return "Сейчас нет активных объявлений."
    return "Список проданных товаров пуст."


def format_status_badge(status: ProductStatus) -> str:
    return "SOLD" if status == ProductStatus.SOLD else "ACTIVE"


def format_category_label(category: ProductCategory) -> str:
    return category.label
