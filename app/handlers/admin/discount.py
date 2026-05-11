from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import Settings
from app.handlers.admin.helpers import is_admin, send_photo_or_text
from app.keyboards.admin import AdminProductActionCallback, active_product_actions_keyboard
from app.services import formatter
from app.services.exceptions import ChannelOperationError, InvalidPriceError, ProductAlreadySoldError, ProductNotFoundError
from app.services.product_service import ProductService
from app.states.product_states import ProductStates

router = Router(name="admin_discount")


@router.callback_query(AdminProductActionCallback.filter(F.action == "discount"))
async def ask_discount_handler(
    callback: CallbackQuery,
    callback_data: AdminProductActionCallback,
    state: FSMContext,
    settings: Settings,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    await state.set_state(ProductStates.waiting_for_discount_price)
    await state.update_data(
        discount_product_id=callback_data.product_id,
        discount_page=callback_data.page,
        discount_status=callback_data.status,
    )
    await callback.answer()
    await callback.message.answer(formatter.format_discount_prompt())


@router.message(ProductStates.waiting_for_discount_price)
async def apply_discount_handler(
    message: Message,
    state: FSMContext,
    settings: Settings,
    product_service: ProductService,
) -> None:
    if message.from_user is None or not is_admin(message.from_user.id, settings):
        await message.answer(formatter.format_no_access_message())
        return

    if not message.text:
        await message.answer(formatter.format_invalid_price_message(), parse_mode="HTML")
        return

    text = message.text.strip()
    if not text.isdigit():
        await message.answer(formatter.format_invalid_price_message(), parse_mode="HTML")
        return

    data = await state.get_data()
    if "discount_product_id" not in data or "discount_page" not in data:
        await state.clear()
        await message.answer(formatter.format_cancelled_message(), parse_mode="HTML")
        return

    product_id = int(data["discount_product_id"])
    page = int(data["discount_page"])
    new_price = int(text)
    try:
        product = await product_service.apply_discount(
            admin_id=message.from_user.id,
            product_id=product_id,
            new_price=new_price,
        )
    except ProductNotFoundError:
        await state.clear()
        await message.answer(formatter.format_product_not_found_message(), parse_mode="HTML")
        return
    except ProductAlreadySoldError:
        await state.clear()
        await message.answer(formatter.format_discount_blocked_message(), parse_mode="HTML")
        return
    except InvalidPriceError:
        await message.answer(formatter.format_discount_must_be_lower_message(), parse_mode="HTML")
        return
    except ChannelOperationError:
        await state.clear()
        await message.answer(formatter.format_channel_error_message(), parse_mode="HTML")
        return

    await state.clear()
    await message.answer(formatter.format_discount_success_message(), parse_mode="HTML")
    await send_photo_or_text(
        message,
        text=formatter.format_admin_product_card(product, settings.support_username),
        photo_file_ids=[photo.file_id for photo in product.photos],
        reply_markup=active_product_actions_keyboard(
            product_id=product.id,
            page=page,
            has_discount=product.old_price is not None,
        ),
    )


@router.callback_query(AdminProductActionCallback.filter(F.action == "remove_discount"))
async def remove_discount_handler(
    callback: CallbackQuery,
    callback_data: AdminProductActionCallback,
    settings: Settings,
    product_service: ProductService,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    try:
        product = await product_service.remove_discount(
            admin_id=callback.from_user.id,
            product_id=callback_data.product_id,
        )
    except ProductNotFoundError:
        await callback.answer()
        await callback.message.answer(formatter.format_product_not_found_message(), parse_mode="HTML")
        return
    except ProductAlreadySoldError:
        await callback.answer()
        await callback.message.answer(formatter.format_discount_blocked_message(), parse_mode="HTML")
        return
    except InvalidPriceError:
        await callback.answer()
        await callback.message.answer(formatter.format_discount_must_be_lower_message(), parse_mode="HTML")
        return
    except ChannelOperationError:
        await callback.answer()
        await callback.message.answer(formatter.format_channel_error_message(), parse_mode="HTML")
        return

    await callback.answer()
    await callback.message.answer(formatter.format_discount_removed_message(), parse_mode="HTML")
    await send_photo_or_text(
        callback,
        text=formatter.format_admin_product_card(product, settings.support_username),
        photo_file_ids=[photo.file_id for photo in product.photos],
        reply_markup=active_product_actions_keyboard(
            product_id=product.id,
            page=callback_data.page,
            has_discount=product.old_price is not None,
        ),
    )
