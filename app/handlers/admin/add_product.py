from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import Settings
from app.constants import ADMIN_MENU_ADD
from app.database.models import ProductCategory, ProductStatus
from app.handlers.admin.helpers import is_admin, send_preview
from app.keyboards.admin import (
    AdminAddCategoryCallback,
    AdminEditFieldCallback,
    AdminPreviewActionCallback,
    admin_menu_keyboard,
    category_inline_keyboard,
    edit_fields_keyboard,
    photo_collection_keyboard,
)
from app.services import formatter
from app.services.exceptions import ChannelOperationError, InvalidPriceError
from app.services.product_service import ProductDraft, ProductService
from app.services.product_service import ProductUpdate
from app.utils.pricing import parse_price
from app.states.product_states import ProductStates

router = Router(name="admin_add_product")

REQUIRED_DRAFT_FIELDS = {"photo_file_ids", "title", "size", "price", "condition", "category"}


@router.message(F.text == ADMIN_MENU_ADD)
async def start_add_product_handler(
    message: Message,
    settings: Settings,
    state: FSMContext,
    product_service: ProductService,
) -> None:
    if message.from_user is None or not is_admin(message.from_user.id, settings):
        await message.answer(formatter.format_no_access_message())
        return

    await state.clear()
    await state.set_state(ProductStates.waiting_for_photos)
    await state.update_data(photo_file_ids=[], status=ProductStatus.ACTIVE.value)
    await product_service.record_admin_action(admin_id=message.from_user.id, action="START_ADD_PRODUCT")
    await message.answer(
        formatter.format_photo_prompt(),
        parse_mode="HTML",
        reply_markup=photo_collection_keyboard(can_finish=False),
    )


@router.callback_query(F.data == "admin:add")
async def start_add_product_callback_handler(
    callback: CallbackQuery,
    settings: Settings,
    state: FSMContext,
    product_service: ProductService,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    await state.clear()
    await state.set_state(ProductStates.waiting_for_photos)
    await state.update_data(photo_file_ids=[], status=ProductStatus.ACTIVE.value)
    await product_service.record_admin_action(admin_id=callback.from_user.id, action="START_ADD_PRODUCT")
    await callback.answer()
    await callback.message.edit_text(
        formatter.format_photo_prompt(),
        parse_mode="HTML",
        reply_markup=photo_collection_keyboard(can_finish=False),
    )


@router.message(ProductStates.waiting_for_photos, F.photo)
@router.message(ProductStates.editing_photos, F.photo)
async def product_photo_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    photo_file_ids: list[str] = list(data.get("photo_file_ids", []))
    if len(photo_file_ids) >= 5:
        await message.answer(formatter.format_photo_limit_message(), parse_mode="HTML")
        return

    photo_file_id = message.photo[-1].file_id
    if photo_file_id in photo_file_ids:
        await message.answer(
            formatter.format_photo_saved_message(len(photo_file_ids)),
            parse_mode="HTML",
            reply_markup=photo_collection_keyboard(can_finish=True),
        )
        return

    photo_file_ids.append(photo_file_id)
    await state.update_data(photo_file_ids=photo_file_ids)
    await message.answer(
        formatter.format_photo_saved_message(len(photo_file_ids)),
        parse_mode="HTML",
        reply_markup=photo_collection_keyboard(can_finish=True),
    )


@router.message(ProductStates.waiting_for_photos)
@router.message(ProductStates.editing_photos)
async def product_photo_invalid_input_handler(message: Message) -> None:
    await message.answer(formatter.format_photo_prompt(), parse_mode="HTML")


@router.callback_query(AdminPreviewActionCallback.filter(F.action == "photos_done"))
async def photo_collection_done_handler(callback: CallbackQuery, state: FSMContext, settings: Settings) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    data = await state.get_data()
    photo_file_ids: list[str] = list(data.get("photo_file_ids", []))
    if not photo_file_ids:
        await callback.answer("Сначала добавьте хотя бы одно фото.", show_alert=True)
        return

    current_state = await state.get_state()
    await callback.answer()
    if current_state == ProductStates.editing_photos.state:
        await state.set_state(ProductStates.preview)
        await send_preview(callback, state, settings)
        return

    await state.set_state(ProductStates.waiting_for_title)
    await callback.message.answer(formatter.format_enter_title_prompt(), parse_mode="HTML")


@router.message(ProductStates.waiting_for_title)
@router.message(ProductStates.editing_title)
async def title_handler(message: Message, state: FSMContext, settings: Settings) -> None:
    if not message.text:
        await message.answer(formatter.format_enter_title_prompt(), parse_mode="HTML")
        return

    await state.update_data(title=message.text.strip())
    if await state.get_state() == ProductStates.editing_title.state:
        await state.set_state(ProductStates.preview)
        await send_preview(message, state, settings)
        return

    await state.set_state(ProductStates.waiting_for_size)
    await message.answer(formatter.format_enter_size_prompt())


@router.message(ProductStates.waiting_for_size)
@router.message(ProductStates.editing_size)
async def size_handler(message: Message, state: FSMContext, settings: Settings) -> None:
    if not message.text:
        await message.answer(formatter.format_enter_size_prompt())
        return

    await state.update_data(size=message.text.strip())
    if await state.get_state() == ProductStates.editing_size.state:
        await state.set_state(ProductStates.preview)
        await send_preview(message, state, settings)
        return

    await state.set_state(ProductStates.waiting_for_price)
    await message.answer(formatter.format_enter_price_prompt())


@router.message(ProductStates.waiting_for_price)
@router.message(ProductStates.editing_price)
async def price_handler(
    message: Message,
    state: FSMContext,
    settings: Settings,
) -> None:
    if not message.text:
        await message.answer(formatter.format_invalid_price_message(), parse_mode="HTML")
        return

    price = parse_price(message.text)
    if price is None:
        await message.answer(formatter.format_invalid_price_message(), parse_mode="HTML")
        return

    current_state = await state.get_state()
    await state.update_data(price=price)

    if current_state == ProductStates.editing_price.state:
        await state.set_state(ProductStates.preview)
        await send_preview(message, state, settings)
        return

    await state.set_state(ProductStates.waiting_for_condition)
    await message.answer(formatter.format_enter_condition_prompt())


@router.message(ProductStates.waiting_for_condition)
@router.message(ProductStates.editing_condition)
async def condition_handler(message: Message, state: FSMContext, settings: Settings) -> None:
    if not message.text:
        await message.answer(formatter.format_enter_condition_prompt())
        return

    await state.update_data(condition=message.text.strip())
    if await state.get_state() == ProductStates.editing_condition.state:
        await state.set_state(ProductStates.preview)
        await send_preview(message, state, settings)
        return

    await state.set_state(ProductStates.waiting_for_description)
    await message.answer(formatter.format_enter_description_prompt())


@router.message(ProductStates.waiting_for_description)
@router.message(ProductStates.editing_description)
async def description_handler(message: Message, state: FSMContext, settings: Settings) -> None:
    if not message.text:
        await message.answer(formatter.format_enter_description_prompt())
        return

    await state.update_data(description=message.text.strip())
    if await state.get_state() == ProductStates.editing_description.state:
        await state.set_state(ProductStates.preview)
        await send_preview(message, state, settings)
        return

    await state.set_state(ProductStates.waiting_for_category)
    await message.answer(
        formatter.format_choose_category_prompt(),
        reply_markup=category_inline_keyboard(),
    )


@router.message(ProductStates.waiting_for_category)
@router.message(ProductStates.editing_category)
async def category_text_rejected_handler(message: Message) -> None:
    await message.answer(formatter.format_invalid_category_message(), parse_mode="HTML")


@router.callback_query(AdminAddCategoryCallback.filter())
async def category_selected_handler(
    callback: CallbackQuery,
    callback_data: AdminAddCategoryCallback,
    state: FSMContext,
    settings: Settings,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    try:
        ProductCategory(callback_data.category)
    except ValueError:
        await callback.answer()
        await callback.message.answer(formatter.format_invalid_category_message(), parse_mode="HTML")
        return

    data = await state.get_data()
    if not {"photo_file_ids", "title", "size", "price", "condition"}.issubset(data.keys()):
        await state.clear()
        await callback.answer()
        await callback.message.answer(
            formatter.format_cancelled_message(),
            parse_mode="HTML",
            reply_markup=admin_menu_keyboard(),
        )
        return

    await state.update_data(category=callback_data.category, status=ProductStatus.ACTIVE.value)
    await state.set_state(ProductStates.preview)
    await callback.answer()
    await send_preview(callback, state, settings)


@router.callback_query(AdminPreviewActionCallback.filter(F.action == "edit"))
async def edit_preview_handler(callback: CallbackQuery, settings: Settings) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    await callback.answer()
    await callback.message.answer("Что изменить?", reply_markup=edit_fields_keyboard())


@router.callback_query(AdminPreviewActionCallback.filter(F.action == "back_to_preview"))
async def back_to_preview_handler(callback: CallbackQuery, state: FSMContext, settings: Settings) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    data = await state.get_data()
    await callback.answer()
    if not _has_complete_draft(data):
        await state.clear()
        await callback.message.answer(
            formatter.format_cancelled_message(),
            parse_mode="HTML",
            reply_markup=admin_menu_keyboard(),
        )
        return

    await state.set_state(ProductStates.preview)
    await send_preview(callback, state, settings)


@router.callback_query(AdminEditFieldCallback.filter())
async def edit_field_handler(
    callback: CallbackQuery,
    callback_data: AdminEditFieldCallback,
    state: FSMContext,
    settings: Settings,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    field = callback_data.field
    await callback.answer()
    if field == "photos":
        await state.update_data(photo_file_ids=[])
        await state.set_state(ProductStates.editing_photos)
        await callback.message.answer(
            "Отправьте новые фотографии товара. Они заменят текущие фото.",
            reply_markup=photo_collection_keyboard(can_finish=False),
        )
        return
    if field == "title":
        await state.set_state(ProductStates.editing_title)
        await callback.message.answer(formatter.format_enter_title_prompt(), parse_mode="HTML")
        return
    if field == "size":
        await state.set_state(ProductStates.editing_size)
        await callback.message.answer(formatter.format_enter_size_prompt())
        return
    if field == "price":
        await state.set_state(ProductStates.editing_price)
        await callback.message.answer(formatter.format_enter_price_prompt())
        return
    if field == "condition":
        await state.set_state(ProductStates.editing_condition)
        await callback.message.answer(formatter.format_enter_condition_prompt())
        return
    if field == "description":
        await state.set_state(ProductStates.editing_description)
        await callback.message.answer(formatter.format_enter_description_prompt())
        return
    if field == "category":
        await state.set_state(ProductStates.editing_category)
        await callback.message.answer(
            formatter.format_choose_category_prompt(),
            reply_markup=category_inline_keyboard(),
        )
        return

    await callback.message.answer(
        formatter.format_cancelled_message(),
        parse_mode="HTML",
        reply_markup=admin_menu_keyboard(),
    )


@router.callback_query(AdminPreviewActionCallback.filter(F.action == "publish"))
@router.callback_query(AdminPreviewActionCallback.filter(F.action == "save_bot_only"))
async def publish_product_handler(
    callback: CallbackQuery,
    callback_data: AdminPreviewActionCallback,
    state: FSMContext,
    settings: Settings,
    product_service: ProductService,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    data = await state.get_data()
    if not _has_complete_draft(data):
        await state.clear()
        await callback.answer()
        await callback.message.answer(
            formatter.format_cancelled_message(),
            parse_mode="HTML",
            reply_markup=admin_menu_keyboard(),
        )
        return

    try:
        draft = ProductDraft(
            title=data["title"],
            size=data["size"],
            condition=data["condition"],
            description=data.get("description"),
            category=ProductCategory(data["category"]),
            price=int(data["price"]),
            photo_file_ids=list(data["photo_file_ids"]),
        )
    except (TypeError, ValueError):
        await state.clear()
        await callback.answer()
        await callback.message.answer(
            formatter.format_cancelled_message(),
            parse_mode="HTML",
            reply_markup=admin_menu_keyboard(),
        )
        return

    try:
        if data.get("edit_existing_id"):
            await product_service.update_product(
                admin_id=callback.from_user.id,
                product_id=int(data["edit_existing_id"]),
                update=ProductUpdate(
                    title=draft.title,
                    size=draft.size,
                    condition=draft.condition,
                    description=draft.description,
                    category=draft.category,
                    price=draft.price,
                    photo_file_ids=draft.photo_file_ids,
                ),
            )
        else:
            await product_service.publish_product(
                admin_id=callback.from_user.id,
                draft=draft,
                publish_to_channel=callback_data.action == "publish",
            )
    except ChannelOperationError:
        await callback.answer()
        await callback.message.answer(formatter.format_channel_error_message(), parse_mode="HTML")
        return
    except InvalidPriceError:
        await callback.answer()
        await callback.message.answer(formatter.format_invalid_price_message(), parse_mode="HTML")
        return

    await state.clear()
    await callback.answer()
    await callback.message.answer(
        formatter.format_product_published_message(),
        parse_mode="HTML",
        reply_markup=admin_menu_keyboard(),
    )


@router.callback_query(AdminPreviewActionCallback.filter(F.action == "cancel"))
async def cancel_add_product_handler(callback: CallbackQuery, state: FSMContext, settings: Settings) -> None:
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


def _has_complete_draft(data: dict) -> bool:
    if not REQUIRED_DRAFT_FIELDS.issubset(data.keys()):
        return False
    if not isinstance(data.get("photo_file_ids"), list) or not data["photo_file_ids"]:
        return False
    return True
