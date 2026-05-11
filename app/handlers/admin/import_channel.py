from __future__ import annotations

import re
from dataclasses import dataclass
from html import escape
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import Settings
from app.database.models import ProductCategory, ProductSource
from app.handlers.admin.helpers import is_admin
from app.keyboards.admin import (
    AdminImportActionCallback,
    AdminImportCategoryCallback,
    admin_menu_keyboard,
    import_category_keyboard,
    import_collection_keyboard,
)
from app.services import formatter
from app.services.exceptions import InvalidPriceError, InvalidProductStateError
from app.services.product_service import ProductDraft, ProductService
from app.states.product_states import ProductStates
from app.utils import premium_emoji as emoji

router = Router(name="admin_import_channel")


@dataclass(slots=True)
class ParsedImportPost:
    title: str | None
    size: str | None
    condition: str | None
    description: str | None
    price: int | None
    category: ProductCategory | None


@router.callback_query(F.data == "admin:import_channel")
async def start_import_channel_handler(
    callback: CallbackQuery,
    settings: Settings,
    state: FSMContext,
    product_service: ProductService,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    await state.clear()
    await state.set_state(ProductStates.importing_channel_posts)
    await state.update_data(import_messages=[])
    await product_service.record_admin_action(admin_id=callback.from_user.id, action="START_CHANNEL_IMPORT")
    await callback.answer()
    await callback.message.edit_text(
        "Перешлите пост из канала, который нужно добавить в каталог.\n\n"
        "Если это альбом, перешлите все сообщения альбома, затем нажмите «Готово».",
        reply_markup=import_collection_keyboard(can_finish=False),
    )


@router.message(ProductStates.importing_channel_posts)
async def collect_imported_channel_post_handler(message: Message, state: FSMContext) -> None:
    item = _message_to_import_item(message)
    if not item["raw_text"] and not item["raw_caption"] and not item["photo_file_id"]:
        await message.answer(
            "Перешлите пост с текстом или фото из канала.",
            reply_markup=import_collection_keyboard(can_finish=False),
        )
        return

    data = await state.get_data()
    messages: list[dict[str, Any]] = list(data.get("import_messages", []))
    messages.append(item)
    await state.update_data(import_messages=messages)
    photo_count = len(_collect_photo_file_ids(messages))
    await message.answer(
        f"{emoji.CHECK} Пост принят. Фото: {photo_count}/5.",
        parse_mode="HTML",
        reply_markup=import_collection_keyboard(can_finish=True),
    )


@router.callback_query(AdminImportActionCallback.filter(F.action == "cancel"))
async def cancel_import_channel_handler(callback: CallbackQuery, state: FSMContext, settings: Settings) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    await state.clear()
    await callback.answer()
    await callback.message.answer(
        formatter.format_cancelled_message(),
        parse_mode="HTML",
        reply_markup=admin_menu_keyboard(),
    )


@router.callback_query(AdminImportActionCallback.filter(F.action == "done"))
async def finish_collect_import_channel_handler(
    callback: CallbackQuery,
    state: FSMContext,
    settings: Settings,
    product_service: ProductService,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    data = await state.get_data()
    messages: list[dict[str, Any]] = list(data.get("import_messages", []))
    if not messages:
        await callback.answer("Сначала перешлите пост из канала.", show_alert=True)
        return

    await callback.answer()
    await _prepare_or_save_import(callback.message, state, settings, product_service, admin_id=callback.from_user.id)


@router.message(ProductStates.import_waiting_for_title)
async def import_title_handler(message: Message, state: FSMContext, settings: Settings, product_service: ProductService) -> None:
    if not message.text:
        await message.answer("Введите название товара.")
        return
    await state.update_data(import_title=message.text.strip())
    await _prepare_or_save_import(message, state, settings, product_service, admin_id=message.from_user.id if message.from_user else 0)


@router.message(ProductStates.import_waiting_for_size)
async def import_size_handler(message: Message, state: FSMContext, settings: Settings, product_service: ProductService) -> None:
    if not message.text:
        await message.answer("Введите размер товара.")
        return
    await state.update_data(import_size=message.text.strip())
    await _prepare_or_save_import(message, state, settings, product_service, admin_id=message.from_user.id if message.from_user else 0)


@router.message(ProductStates.import_waiting_for_condition)
async def import_condition_handler(message: Message, state: FSMContext, settings: Settings, product_service: ProductService) -> None:
    if not message.text:
        await message.answer("Введите состояние товара.")
        return
    await state.update_data(import_condition=message.text.strip())
    await _prepare_or_save_import(message, state, settings, product_service, admin_id=message.from_user.id if message.from_user else 0)


@router.message(ProductStates.import_waiting_for_price)
async def import_price_handler(message: Message, state: FSMContext, settings: Settings, product_service: ProductService) -> None:
    if not message.text or not message.text.strip().isdigit():
        await message.answer(formatter.format_invalid_price_message(), parse_mode="HTML")
        return
    await state.update_data(import_price=int(message.text.strip()))
    await _prepare_or_save_import(message, state, settings, product_service, admin_id=message.from_user.id if message.from_user else 0)


@router.callback_query(AdminImportCategoryCallback.filter())
async def import_category_handler(
    callback: CallbackQuery,
    callback_data: AdminImportCategoryCallback,
    state: FSMContext,
    settings: Settings,
    product_service: ProductService,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    await callback.answer()
    await state.update_data(import_category=callback_data.category)
    await _prepare_or_save_import(callback.message, state, settings, product_service, admin_id=callback.from_user.id)


async def _prepare_or_save_import(
    message: Message,
    state: FSMContext,
    settings: Settings,
    product_service: ProductService,
    admin_id: int,
) -> None:
    data = await state.get_data()
    messages: list[dict[str, Any]] = list(data.get("import_messages", []))
    import_data = _build_import_data(messages)
    parsed = _parse_import_text(import_data["raw_caption"] or import_data["raw_text"] or "")

    title = data.get("import_title") or parsed.title
    size = data.get("import_size") or parsed.size
    condition = data.get("import_condition") or parsed.condition
    price = data.get("import_price") or parsed.price
    category_value = data.get("import_category")
    category = ProductCategory(category_value) if category_value else parsed.category

    if not title:
        await state.set_state(ProductStates.import_waiting_for_title)
        await message.answer("Не смог распознать название. Введите название товара.")
        return
    if not size:
        await state.set_state(ProductStates.import_waiting_for_size)
        await message.answer("Не смог распознать размер. Введите размер товара.")
        return
    if not condition:
        await state.set_state(ProductStates.import_waiting_for_condition)
        await message.answer("Не смог распознать состояние. Введите состояние товара.")
        return
    if not price:
        await state.set_state(ProductStates.import_waiting_for_price)
        await message.answer("Не смог распознать цену. Введите цену числом.")
        return
    if not category:
        await state.set_state(ProductStates.import_waiting_for_category)
        await message.answer("Выберите категорию товара:", reply_markup=import_category_keyboard())
        return

    if not import_data["photo_file_ids"]:
        await state.set_state(ProductStates.importing_channel_posts)
        await message.answer(
            "В импортируемом посте нет фото. Перешлите пост с фото товара.",
            reply_markup=import_collection_keyboard(can_finish=True),
        )
        return

    try:
        product = await product_service.publish_product(
            admin_id=admin_id,
            draft=ProductDraft(
                title=title,
                size=size,
                condition=condition,
                description=parsed.description,
                category=category,
                price=price,
                photo_file_ids=import_data["photo_file_ids"],
                source=ProductSource.CHANNEL_IMPORT,
                channel_chat_id=import_data["channel_chat_id"],
                channel_message_id=import_data["channel_message_id"],
                channel_media_group_message_ids=import_data["channel_media_group_message_ids"],
                raw_text=import_data["raw_text"],
                raw_caption=import_data["raw_caption"],
                entities_json=import_data["entities_json"],
                caption_entities_json=import_data["caption_entities_json"],
                html_text=import_data["html_text"],
                html_caption=import_data["html_caption"],
            ),
            publish_to_channel=False,
        )
    except (InvalidPriceError, InvalidProductStateError):
        await message.answer(formatter.format_invalid_price_message(), parse_mode="HTML")
        return

    await state.clear()
    await message.answer(
        f"{formatter.format_product_published_message()}\nИмпортирован товар: <b>{escape(product.title)}</b>",
        parse_mode="HTML",
        reply_markup=admin_menu_keyboard(),
    )


def _message_to_import_item(message: Message) -> dict[str, Any]:
    channel_chat_id, channel_message_id = _extract_forward_channel_ref(message)
    photo_file_id = message.photo[-1].file_id if message.photo else None
    return {
        "media_group_id": message.media_group_id,
        "photo_file_id": photo_file_id,
        "raw_text": message.text,
        "raw_caption": message.caption,
        "entities_json": _entities_to_json(message.entities),
        "caption_entities_json": _entities_to_json(message.caption_entities),
        "html_text": getattr(message, "html_text", None),
        "html_caption": getattr(message, "html_caption", None),
        "channel_chat_id": channel_chat_id,
        "channel_message_id": channel_message_id,
    }


def _extract_forward_channel_ref(message: Message) -> tuple[int | None, int | None]:
    origin = getattr(message, "forward_origin", None)
    if origin and getattr(origin, "chat", None) is not None:
        return origin.chat.id, getattr(origin, "message_id", None)
    forward_chat = getattr(message, "forward_from_chat", None)
    if forward_chat is not None:
        return forward_chat.id, getattr(message, "forward_from_message_id", None)
    return None, None


def _entities_to_json(entities) -> list[dict] | None:
    if not entities:
        return None
    return [entity.model_dump(mode="json", exclude_none=True) for entity in entities]


def _build_import_data(messages: list[dict[str, Any]]) -> dict[str, Any]:
    primary = next((item for item in messages if item.get("raw_caption") or item.get("raw_text")), messages[0])
    photo_file_ids = _collect_photo_file_ids(messages)
    channel_message_ids = [
        item["channel_message_id"]
        for item in messages
        if item.get("channel_message_id") is not None and item.get("photo_file_id")
    ]
    return {
        "photo_file_ids": photo_file_ids[:5],
        "raw_text": primary.get("raw_text"),
        "raw_caption": primary.get("raw_caption"),
        "entities_json": primary.get("entities_json"),
        "caption_entities_json": primary.get("caption_entities_json"),
        "html_text": primary.get("html_text"),
        "html_caption": primary.get("html_caption"),
        "channel_chat_id": primary.get("channel_chat_id"),
        "channel_message_id": primary.get("channel_message_id"),
        "channel_media_group_message_ids": list(dict.fromkeys(channel_message_ids)) or None,
    }


def _collect_photo_file_ids(messages: list[dict[str, Any]]) -> list[str]:
    return list(dict.fromkeys(item["photo_file_id"] for item in messages if item.get("photo_file_id")))


def _parse_import_text(text: str) -> ParsedImportPost:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = None
    size = None
    condition = None
    price = None
    description_lines: list[str] = []

    for line in lines:
        lower = line.lower()
        if lower.startswith("размер"):
            size = _value_after_colon_or_space(line, "Размер")
            continue
        if lower.startswith("состояние"):
            condition = _value_after_colon_or_space(line, "Состояние")
            continue
        if lower.startswith("цена"):
            match = re.search(r"(\d[\d\s]*)", line)
            if match:
                price = int(match.group(1).replace(" ", ""))
            continue
        if line.startswith("#") or "админ" in lower or "в наличии" in lower or "sold" in lower:
            continue
        if title is None:
            title = line
            continue
        description_lines.append(line)

    return ParsedImportPost(
        title=title,
        size=size,
        condition=condition,
        description="\n".join(description_lines) if description_lines else None,
        price=price,
        category=_infer_category(text),
    )


def _value_after_colon_or_space(line: str, label: str) -> str | None:
    value = re.sub(rf"^{label}\s*:?\s*", "", line, flags=re.IGNORECASE).strip()
    return value or None


def _infer_category(text: str) -> ProductCategory | None:
    normalized = text.lower()
    if any(word in normalized for word in ("кроссов", "ботин", "обув", "air force", "nike", "adidas")):
        return ProductCategory.SHOES
    if any(word in normalized for word in ("худи", "кофта", "штаны", "джинсы", "футбол", "куртка", "одеж")):
        return ProductCategory.CLOTHING
    if any(word in normalized for word in ("сумка", "ремень", "очки", "аксесс")):
        return ProductCategory.ACCESSORIES
    return None
