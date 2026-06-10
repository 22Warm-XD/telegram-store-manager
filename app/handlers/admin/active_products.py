from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import Settings
from app.constants import ADMIN_MENU_ACTIVE
from app.database.models import ProductStatus
from app.handlers.admin.helpers import is_admin, send_photo_or_text
from app.keyboards.admin import (
    AdminProductActionCallback,
    AdminProductViewCallback,
    AdminProductsPageCallback,
    active_product_actions_keyboard,
    admin_products_keyboard,
    delete_product_confirmation_keyboard,
    edit_fields_keyboard,
)
from app.services import formatter
from app.services.exceptions import ProductNotFoundError
from app.services.product_service import ProductService
from app.states.product_states import ProductStates

router = Router(name="admin_active_products")


@router.callback_query(AdminProductActionCallback.filter(F.action == "edit"))
async def edit_active_product_handler(
    callback: CallbackQuery,
    callback_data: AdminProductActionCallback,
    settings: Settings,
    state: FSMContext,
    product_service: ProductService,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return
    try:
        product = await product_service.get_product(callback_data.product_id)
    except ProductNotFoundError:
        await callback.answer(formatter.format_product_not_found_message(), show_alert=True)
        return
    await state.clear()
    await state.update_data(
        edit_existing_id=product.id,
        edit_existing_page=callback_data.page,
        photo_file_ids=[photo.file_id for photo in product.photos],
        title=product.title,
        size=product.size,
        price=product.price,
        condition=product.condition,
        description=product.description or "0",
        category=product.category.value,
        status=product.status.value,
    )
    await state.set_state(ProductStates.preview)
    await callback.answer()
    await callback.message.answer(
        "Что изменить в товаре?",
        reply_markup=edit_fields_keyboard(),
    )


@router.callback_query(AdminProductActionCallback.filter(F.action == "delete"))
async def ask_delete_active_product_handler(
    callback: CallbackQuery,
    callback_data: AdminProductActionCallback,
    settings: Settings,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return
    await callback.answer()
    await callback.message.answer(
        "Удалить товар из витрины? Это действие скроет его из каталога.",
        reply_markup=delete_product_confirmation_keyboard(
            product_id=callback_data.product_id,
            page=callback_data.page,
        ),
    )


@router.callback_query(AdminProductActionCallback.filter(F.action == "delete_confirm"))
async def delete_active_product_handler(
    callback: CallbackQuery,
    callback_data: AdminProductActionCallback,
    settings: Settings,
    product_service: ProductService,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return
    try:
        await product_service.delete_product(
            admin_id=callback.from_user.id,
            product_id=callback_data.product_id,
        )
    except ProductNotFoundError:
        await callback.answer(formatter.format_product_not_found_message(), show_alert=True)
        return
    await callback.answer("Товар удалён.")
    await _send_active_products_page(callback, product_service=product_service, page=callback_data.page)


@router.message(F.text == ADMIN_MENU_ACTIVE)
async def active_products_handler(
    message: Message,
    settings: Settings,
    product_service: ProductService,
) -> None:
    if message.from_user is None or not is_admin(message.from_user.id, settings):
        await message.answer(formatter.format_no_access_message())
        return

    await product_service.record_admin_action(admin_id=message.from_user.id, action="VIEW_ACTIVE_PRODUCTS")
    await _send_active_products_page(message, product_service=product_service, page=1)


@router.callback_query(F.data == "admin:active")
async def active_products_callback_handler(
    callback: CallbackQuery,
    settings: Settings,
    product_service: ProductService,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    await product_service.record_admin_action(admin_id=callback.from_user.id, action="VIEW_ACTIVE_PRODUCTS")
    await callback.answer()
    await _send_active_products_page(callback, product_service=product_service, page=1)


@router.callback_query(AdminProductsPageCallback.filter(F.status == ProductStatus.ACTIVE.value))
async def active_products_page_handler(
    callback: CallbackQuery,
    callback_data: AdminProductsPageCallback,
    settings: Settings,
    product_service: ProductService,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    await callback.answer()
    await _send_active_products_page(callback, product_service=product_service, page=callback_data.page)


@router.callback_query(AdminProductViewCallback.filter(F.status == ProductStatus.ACTIVE.value))
async def active_product_detail_handler(
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
        reply_markup=active_product_actions_keyboard(
            product_id=product.id,
            page=callback_data.page,
            has_discount=product.old_price is not None,
        ),
    )


async def _send_active_products_page(
    target: Message | CallbackQuery,
    *,
    product_service: ProductService,
    page: int,
) -> None:
    paginated = await product_service.list_admin_products(status=ProductStatus.ACTIVE, page=page)
    message = target.message if isinstance(target, CallbackQuery) else target
    if not paginated.items:
        await message.answer(formatter.format_empty_list_message(ProductStatus.ACTIVE))
        return

    markup = admin_products_keyboard(
        products=paginated.items,
        status=ProductStatus.ACTIVE,
        page=paginated.page,
        total_pages=paginated.total_pages,
    )
    if isinstance(target, CallbackQuery):
        await _edit_or_answer_text(message, "Активные объявления:", reply_markup=markup)
        return
    await message.answer("Активные объявления:", reply_markup=markup)


async def _edit_or_answer_text(message: Message, text: str, *, reply_markup) -> None:
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest:
        await message.answer(text, reply_markup=reply_markup)
