from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message

from app.config import Settings
from app.constants import ADMIN_MENU_SOLD
from app.database.models import ProductStatus
from app.handlers.admin.helpers import is_admin, send_photo_or_text
from app.keyboards.admin import (
    AdminProductActionCallback,
    AdminProductViewCallback,
    AdminProductsPageCallback,
    admin_products_keyboard,
    sold_product_actions_keyboard,
)
from app.services import formatter
from app.services.exceptions import ChannelOperationError, InvalidProductStateError, ProductAlreadySoldError, ProductNotFoundError
from app.services.product_service import ProductService

router = Router(name="admin_sold")


@router.callback_query(AdminProductActionCallback.filter(F.action == "mark_sold"))
async def mark_product_as_sold_handler(
    callback: CallbackQuery,
    callback_data: AdminProductActionCallback,
    settings: Settings,
    product_service: ProductService,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    try:
        await product_service.mark_as_sold(admin_id=callback.from_user.id, product_id=callback_data.product_id)
    except ProductAlreadySoldError:
        await callback.answer()
        await callback.message.answer(formatter.format_discount_blocked_message(), parse_mode="HTML")
        return
    except ProductNotFoundError:
        await callback.answer()
        await callback.message.answer(formatter.format_product_not_found_message(), parse_mode="HTML")
        return
    except ChannelOperationError:
        await callback.answer()
        await callback.message.answer(formatter.format_channel_error_message(), parse_mode="HTML")
        return

    await callback.answer()
    await callback.message.answer(formatter.format_sold_success_message(), parse_mode="HTML")


@router.message(F.text == ADMIN_MENU_SOLD)
async def sold_products_handler(
    message: Message,
    settings: Settings,
    product_service: ProductService,
) -> None:
    if message.from_user is None or not is_admin(message.from_user.id, settings):
        await message.answer(formatter.format_no_access_message())
        return

    await product_service.record_admin_action(admin_id=message.from_user.id, action="VIEW_SOLD_PRODUCTS")
    await _send_sold_products_page(message, product_service=product_service, page=1)


@router.callback_query(F.data == "admin:sold")
async def sold_products_callback_handler(
    callback: CallbackQuery,
    settings: Settings,
    product_service: ProductService,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    await product_service.record_admin_action(admin_id=callback.from_user.id, action="VIEW_SOLD_PRODUCTS")
    await callback.answer()
    await _send_sold_products_page(callback, product_service=product_service, page=1)


@router.callback_query(AdminProductsPageCallback.filter(F.status == ProductStatus.SOLD.value))
async def sold_products_page_handler(
    callback: CallbackQuery,
    callback_data: AdminProductsPageCallback,
    settings: Settings,
    product_service: ProductService,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    await callback.answer()
    await _send_sold_products_page(callback, product_service=product_service, page=callback_data.page)


@router.callback_query(AdminProductViewCallback.filter(F.status == ProductStatus.SOLD.value))
async def sold_product_detail_handler(
    callback: CallbackQuery,
    callback_data: AdminProductViewCallback,
    settings: Settings,
    product_service: ProductService,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    await callback.answer()
    try:
        product = await product_service.get_product(callback_data.product_id)
    except ProductNotFoundError:
        await callback.message.answer(formatter.format_product_not_found_message(), parse_mode="HTML")
        return

    await send_photo_or_text(
        callback,
        text=formatter.format_admin_product_card(product, settings.support_username),
        photo_file_ids=[photo.file_id for photo in product.photos],
        reply_markup=sold_product_actions_keyboard(product_id=product.id, page=callback_data.page),
    )


@router.callback_query(AdminProductActionCallback.filter(F.action == "archive"))
async def archive_sold_product_handler(
    callback: CallbackQuery,
    callback_data: AdminProductActionCallback,
    settings: Settings,
    product_service: ProductService,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    try:
        await product_service.archive_sold_product(
            admin_id=callback.from_user.id,
            product_id=callback_data.product_id,
        )
    except ProductNotFoundError:
        await callback.answer()
        await callback.message.answer(formatter.format_product_not_found_message(), parse_mode="HTML")
        return
    except InvalidProductStateError:
        await callback.answer()
        await callback.message.answer(formatter.format_product_not_found_message(), parse_mode="HTML")
        return

    await callback.answer()
    await callback.message.answer(formatter.format_archive_success_message(), parse_mode="HTML")


async def _send_sold_products_page(
    target: Message | CallbackQuery,
    *,
    product_service: ProductService,
    page: int,
) -> None:
    paginated = await product_service.list_admin_products(status=ProductStatus.SOLD, page=page)
    message = target.message if isinstance(target, CallbackQuery) else target
    if not paginated.items:
        await message.answer(formatter.format_empty_list_message(ProductStatus.SOLD))
        return

    markup = admin_products_keyboard(
        products=paginated.items,
        status=ProductStatus.SOLD,
        page=paginated.page,
        total_pages=paginated.total_pages,
    )
    if isinstance(target, CallbackQuery):
        await _edit_or_answer_text(message, "Проданные товары:", reply_markup=markup)
        return
    await message.answer("Проданные товары:", reply_markup=markup)


async def _edit_or_answer_text(message: Message, text: str, *, reply_markup) -> None:
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest:
        await message.answer(text, reply_markup=reply_markup)
