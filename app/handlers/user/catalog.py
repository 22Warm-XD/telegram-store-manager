from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import Settings
from app.constants import MAIN_MENU_CATALOG
from app.database.models import ProductCategory
from app.keyboards.catalog import (
    CatalogCategoryCallback,
    CatalogListCallback,
    CatalogProductCallback,
    catalog_categories_keyboard,
    catalog_products_keyboard,
    product_detail_keyboard,
)
from app.services import formatter
from app.services.exceptions import ProductNotFoundError
from app.services.product_service import ProductService

router = Router(name="user_catalog")
CATALOG_MESSAGE_ID_KEY = "catalog_message_id"


@router.message(F.text == MAIN_MENU_CATALOG)
async def open_catalog_handler(message: Message, state: FSMContext, settings: Settings) -> None:
    await _delete_previous_catalog_message(message, state)
    sent_message = await message.answer(
        formatter.format_catalog_message(),
        parse_mode="HTML",
        reply_markup=catalog_categories_keyboard(reviews_url=settings.reviews_url, support_url=settings.support_url),
    )
    await state.update_data(**{CATALOG_MESSAGE_ID_KEY: sent_message.message_id})


@router.callback_query(F.data == "main:catalog")
async def open_catalog_callback(callback: CallbackQuery, state: FSMContext, settings: Settings) -> None:
    await callback.answer()
    await _replace_with_text(
        callback.message,
        state,
        text=formatter.format_catalog_message(),
        parse_mode="HTML",
        reply_markup=catalog_categories_keyboard(reviews_url=settings.reviews_url, support_url=settings.support_url),
    )


@router.message(F.text.in_([category.label for category in ProductCategory]))
async def category_handler(message: Message, state: FSMContext, product_service: ProductService) -> None:
    category = ProductCategory.from_label(message.text)
    await _send_category_products(message, state=state, product_service=product_service, category=category, page=1)


@router.callback_query(CatalogCategoryCallback.filter())
async def category_callback_handler(
    callback: CallbackQuery,
    callback_data: CatalogCategoryCallback,
    state: FSMContext,
    product_service: ProductService,
    settings: Settings,
) -> None:
    await callback.answer()
    try:
        category = ProductCategory(callback_data.category)
    except ValueError:
        await callback.message.edit_text(formatter.format_product_not_found_message(), parse_mode="HTML")
        return
    await _send_category_products(
        callback,
        state=state,
        product_service=product_service,
        category=category,
        page=1,
        settings=settings,
    )


@router.callback_query(CatalogListCallback.filter())
async def catalog_page_handler(
    callback: CallbackQuery,
    callback_data: CatalogListCallback,
    state: FSMContext,
    product_service: ProductService,
    settings: Settings,
) -> None:
    await callback.answer()
    try:
        category = ProductCategory(callback_data.category)
    except ValueError:
        await callback.message.answer(formatter.format_product_not_found_message(), parse_mode="HTML")
        return
    await _send_category_products(
        callback,
        state=state,
        product_service=product_service,
        category=category,
        page=callback_data.page,
        settings=settings,
    )


@router.callback_query(F.data == "catalog:categories")
async def back_to_categories_handler(callback: CallbackQuery, state: FSMContext, settings: Settings) -> None:
    await callback.answer()
    await _replace_with_text(
        callback.message,
        state,
        text=formatter.format_catalog_message(),
        parse_mode="HTML",
        reply_markup=catalog_categories_keyboard(reviews_url=settings.reviews_url, support_url=settings.support_url),
    )


@router.callback_query(CatalogProductCallback.filter())
async def product_detail_handler(
    callback: CallbackQuery,
    callback_data: CatalogProductCallback,
    state: FSMContext,
    product_service: ProductService,
    settings: Settings,
) -> None:
    await callback.answer()
    try:
        category = ProductCategory(callback_data.category)
    except ValueError:
        await callback.message.answer(formatter.format_product_not_found_message(), parse_mode="HTML")
        return

    try:
        product = await product_service.get_product(callback_data.product_id)
    except ProductNotFoundError:
        await callback.message.answer(formatter.format_product_not_found_message(), parse_mode="HTML")
        return

    text = formatter.format_product_card(product, settings.support_username)
    photo_file_id = product.photos[0].file_id if product.photos else None
    await _delete_previous_catalog_message(callback.message, state)
    if photo_file_id:
        sent_message = await callback.message.answer_photo(
            photo=photo_file_id,
            caption=text,
            parse_mode="HTML",
            reply_markup=product_detail_keyboard(
                support_url=settings.support_url,
                category=category,
                page=callback_data.page,
            ),
        )
        await state.update_data(**{CATALOG_MESSAGE_ID_KEY: sent_message.message_id})
        return
    sent_message = await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=product_detail_keyboard(
            support_url=settings.support_url,
            category=category,
            page=callback_data.page,
        ),
    )
    await state.update_data(**{CATALOG_MESSAGE_ID_KEY: sent_message.message_id})


@router.callback_query(F.data == "catalog:noop")
async def noop_callback(callback: CallbackQuery) -> None:
    await callback.answer()


async def _send_category_products(
    target: Message | CallbackQuery,
    *,
    state: FSMContext,
    product_service: ProductService,
    category: ProductCategory,
    page: int,
    settings: Settings | None = None,
) -> None:
    paginated = await product_service.list_catalog_products(category=category, page=page)
    message = target.message if isinstance(target, CallbackQuery) else target
    if not isinstance(target, CallbackQuery):
        await _delete_previous_catalog_message(message, state)
    if not paginated.items:
        categories_markup = catalog_categories_keyboard(
            reviews_url=settings.reviews_url if settings else None,
            support_url=settings.support_url if settings else None,
        )
        if isinstance(target, CallbackQuery):
            await _replace_with_text(
                message,
                state,
                text=formatter.format_empty_category_message(),
                reply_markup=categories_markup,
            )
            return
        sent_message = await message.answer(
            formatter.format_empty_category_message(),
            reply_markup=categories_markup,
        )
        await state.update_data(**{CATALOG_MESSAGE_ID_KEY: sent_message.message_id})
        return

    text = f"Категория: <b>{category.label}</b>\nВыберите товар из списка."
    markup = catalog_products_keyboard(
        products=paginated.items,
        category=category,
        page=paginated.page,
        total_pages=paginated.total_pages,
    )
    if isinstance(target, CallbackQuery):
        await _replace_with_text(message, state, text=text, parse_mode="HTML", reply_markup=markup)
        return
    sent_message = await message.answer(text, parse_mode="HTML", reply_markup=markup)
    await state.update_data(**{CATALOG_MESSAGE_ID_KEY: sent_message.message_id})


async def _delete_previous_catalog_message(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    message_id = data.get(CATALOG_MESSAGE_ID_KEY)
    if not message_id:
        return

    try:
        await message.bot.delete_message(chat_id=message.chat.id, message_id=int(message_id))
    except (TelegramAPIError, TypeError, ValueError):
        return


async def _replace_with_text(
    message: Message,
    state: FSMContext,
    *,
    text: str,
    parse_mode: str | None = None,
    reply_markup=None,
) -> None:
    try:
        await message.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
        await state.update_data(**{CATALOG_MESSAGE_ID_KEY: message.message_id})
        return
    except TelegramAPIError:
        pass

    try:
        await message.delete()
    except TelegramAPIError:
        pass
    sent_message = await message.answer(text, parse_mode=parse_mode, reply_markup=reply_markup)
    await state.update_data(**{CATALOG_MESSAGE_ID_KEY: sent_message.message_id})
