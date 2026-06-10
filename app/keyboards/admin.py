from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.constants import (
    ADMIN_MENU_ACTIVE,
    ADMIN_MENU_ADD,
    ADMIN_MENU_IMPORT,
    ADMIN_MENU_SOLD,
    ADMIN_MENU_DESIGN,
    BUTTON_BACK_TO_PREVIEW,
    BUTTON_CANCEL,
    BUTTON_DELETE_FROM_LIST,
    BUTTON_DISCOUNT,
    BUTTON_DONE,
    BUTTON_EDIT,
    BUTTON_EDIT_PRODUCT,
    BUTTON_DELETE_PRODUCT,
    BUTTON_MARK_SOLD,
    BUTTON_PUBLISH,
    BUTTON_SAVE_BOT_ONLY,
    BUTTON_REMOVE_DISCOUNT,
    MAIN_MENU_BACK,
)
from app.database.models import Product, ProductCategory, ProductStatus
from app.keyboards.styles import STYLE_DANGER, STYLE_PRIMARY, STYLE_SUCCESS, add_inline_button
from app.utils import premium_emoji as emoji

SHOES_BUTTON_EMOJI_ID = "5355227496830743755"
CLOTHING_BUTTON_EMOJI_ID = "5204249655390525007"
ACCESSORIES_BUTTON_EMOJI_ID = "5848143571789550128"


class AdminAddCategoryCallback(CallbackData, prefix="admin_add_cat"):
    category: str


class AdminPreviewActionCallback(CallbackData, prefix="admin_preview"):
    action: str


class AdminEditFieldCallback(CallbackData, prefix="admin_edit_field"):
    field: str


class AdminProductsPageCallback(CallbackData, prefix="admin_products_page"):
    status: str
    page: int


class AdminProductViewCallback(CallbackData, prefix="admin_product_view"):
    status: str
    product_id: int
    page: int


class AdminProductActionCallback(CallbackData, prefix="admin_product_action"):
    action: str
    product_id: int
    page: int
    status: str


class AdminImportActionCallback(CallbackData, prefix="admin_import"):
    action: str


class AdminImportCategoryCallback(CallbackData, prefix="admin_import_cat"):
    category: str


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_inline_button(
        builder,
        text=ADMIN_MENU_ADD,
        callback_data="admin:add",
        style=STYLE_SUCCESS,
        icon_custom_emoji_id=emoji.TAG_ID,
    )
    add_inline_button(
        builder,
        text=ADMIN_MENU_IMPORT,
        callback_data="admin:import_channel",
        style=STYLE_PRIMARY,
        icon_custom_emoji_id=emoji.MEDIA_ID,
    )
    add_inline_button(
        builder,
        text=ADMIN_MENU_ACTIVE,
        callback_data="admin:active",
        style=STYLE_PRIMARY,
        icon_custom_emoji_id=emoji.SHIELD_ID,
    )
    add_inline_button(
        builder,
        text=ADMIN_MENU_SOLD,
        callback_data="admin:sold",
        style=STYLE_PRIMARY,
        icon_custom_emoji_id=emoji.CROSS_ID,
    )
    add_inline_button(
        builder,
        text=ADMIN_MENU_DESIGN,
        callback_data="admin:design",
        style=STYLE_PRIMARY,
        icon_custom_emoji_id=emoji.MEDIA_ID,
    )
    add_inline_button(builder, text=MAIN_MENU_BACK, callback_data="main:home", icon_custom_emoji_id=emoji.REFRESH_ID)
    builder.adjust(1)
    return builder.as_markup()


def photo_collection_keyboard(*, can_finish: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if can_finish:
        add_inline_button(
            builder,
            text=BUTTON_DONE,
            callback_data=AdminPreviewActionCallback(action="photos_done"),
            style=STYLE_SUCCESS,
            icon_custom_emoji_id=emoji.CHECK_ID,
        )
    add_inline_button(
        builder,
        text=BUTTON_CANCEL,
        callback_data=AdminPreviewActionCallback(action="cancel"),
        style=STYLE_DANGER,
        icon_custom_emoji_id=emoji.CROSS_ID,
    )
    return builder.as_markup()


def category_inline_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    category_emoji_ids = {
        ProductCategory.SHOES: SHOES_BUTTON_EMOJI_ID,
        ProductCategory.CLOTHING: CLOTHING_BUTTON_EMOJI_ID,
        ProductCategory.ACCESSORIES: ACCESSORIES_BUTTON_EMOJI_ID,
    }
    for category in ProductCategory:
        add_inline_button(
            builder,
            text=category.label,
            callback_data=AdminAddCategoryCallback(category=category.value),
            icon_custom_emoji_id=category_emoji_ids[category],
        )
    builder.adjust(1)
    return builder.as_markup()


def import_collection_keyboard(*, can_finish: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if can_finish:
        add_inline_button(
            builder,
            text=BUTTON_DONE,
            callback_data=AdminImportActionCallback(action="done"),
            style=STYLE_SUCCESS,
            icon_custom_emoji_id=emoji.CHECK_ID,
        )
    add_inline_button(
        builder,
        text=BUTTON_CANCEL,
        callback_data=AdminImportActionCallback(action="cancel"),
        style=STYLE_DANGER,
        icon_custom_emoji_id=emoji.CROSS_ID,
    )
    builder.adjust(1)
    return builder.as_markup()


def import_category_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    category_emoji_ids = {
        ProductCategory.SHOES: SHOES_BUTTON_EMOJI_ID,
        ProductCategory.CLOTHING: CLOTHING_BUTTON_EMOJI_ID,
        ProductCategory.ACCESSORIES: ACCESSORIES_BUTTON_EMOJI_ID,
    }
    for category in ProductCategory:
        add_inline_button(
            builder,
            text=category.label,
            callback_data=AdminImportCategoryCallback(category=category.value),
            icon_custom_emoji_id=category_emoji_ids[category],
        )
    builder.adjust(1)
    return builder.as_markup()


def preview_actions_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_inline_button(
        builder,
        text=BUTTON_PUBLISH,
        callback_data=AdminPreviewActionCallback(action="publish"),
        style=STYLE_SUCCESS,
        icon_custom_emoji_id=emoji.CHECK_ID,
    )
    add_inline_button(
        builder,
        text=BUTTON_SAVE_BOT_ONLY,
        callback_data=AdminPreviewActionCallback(action="save_bot_only"),
        style=STYLE_PRIMARY,
        icon_custom_emoji_id=emoji.SHOP_ID,
    )
    add_inline_button(
        builder,
        text=BUTTON_EDIT,
        callback_data=AdminPreviewActionCallback(action="edit"),
        style=STYLE_PRIMARY,
        icon_custom_emoji_id=emoji.REFRESH_ID,
    )
    add_inline_button(
        builder,
        text=BUTTON_CANCEL,
        callback_data=AdminPreviewActionCallback(action="cancel"),
        style=STYLE_DANGER,
        icon_custom_emoji_id=emoji.CROSS_ID,
    )
    builder.adjust(1)
    return builder.as_markup()


def edit_fields_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for field in ("photos", "title", "size", "price", "condition", "description", "category"):
        labels = {
            "photos": "Фото",
            "title": "Название",
            "size": "Размер",
            "price": "Цена",
            "condition": "Состояние",
            "description": "Описание",
            "category": "Категория",
        }
        add_inline_button(builder, text=labels[field], callback_data=AdminEditFieldCallback(field=field))
    add_inline_button(
        builder,
        text=BUTTON_BACK_TO_PREVIEW,
        callback_data=AdminPreviewActionCallback(action="back_to_preview"),
        icon_custom_emoji_id=emoji.REFRESH_ID,
    )
    builder.adjust(1)
    return builder.as_markup()


def admin_products_keyboard(
    *,
    products: list[Product],
    status: ProductStatus,
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for product in products:
        suffix = "SOLD" if status == ProductStatus.SOLD else f"{product.price} ₽"
        add_inline_button(
            builder,
            text=f"{product.title} — {suffix}",
            callback_data=AdminProductViewCallback(status=status.value, product_id=product.id, page=page),
        )
    builder.adjust(1)

    if total_pages > 1:
        if page > 1:
            add_inline_button(
                builder,
                text="⬅️",
                callback_data=AdminProductsPageCallback(status=status.value, page=page - 1),
            )
        add_inline_button(builder, text=f"{page}/{total_pages}", callback_data="admin:noop")
        if page < total_pages:
            add_inline_button(
                builder,
                text="➡️",
                callback_data=AdminProductsPageCallback(status=status.value, page=page + 1),
            )
        builder.adjust(1, 3)

    add_inline_button(builder, text="Назад", callback_data="admin:menu", icon_custom_emoji_id=emoji.REFRESH_ID)
    return builder.as_markup()


def active_product_actions_keyboard(*, product_id: int, page: int, has_discount: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_inline_button(
        builder,
        text=BUTTON_EDIT_PRODUCT,
        style=STYLE_PRIMARY,
        icon_custom_emoji_id=emoji.REFRESH_ID,
        callback_data=AdminProductActionCallback(
            action="edit",
            product_id=product_id,
            page=page,
            status=ProductStatus.ACTIVE.value,
        ),
    )
    add_inline_button(
        builder,
        text=BUTTON_DISCOUNT,
        style=STYLE_SUCCESS,
        icon_custom_emoji_id=emoji.FIRE_ID,
        callback_data=AdminProductActionCallback(
            action="discount",
            product_id=product_id,
            page=page,
            status=ProductStatus.ACTIVE.value,
        ),
    )
    if has_discount:
        add_inline_button(
            builder,
            text=BUTTON_REMOVE_DISCOUNT,
            style=STYLE_PRIMARY,
            icon_custom_emoji_id=emoji.REFRESH_ID,
            callback_data=AdminProductActionCallback(
                action="remove_discount",
                product_id=product_id,
                page=page,
                status=ProductStatus.ACTIVE.value,
            ),
        )
    add_inline_button(
        builder,
        text=BUTTON_MARK_SOLD,
        style=STYLE_DANGER,
        icon_custom_emoji_id=emoji.CROSS_ID,
        callback_data=AdminProductActionCallback(
            action="mark_sold",
            product_id=product_id,
            page=page,
            status=ProductStatus.ACTIVE.value,
        ),
    )
    add_inline_button(
        builder,
        text=BUTTON_DELETE_PRODUCT,
        style=STYLE_DANGER,
        icon_custom_emoji_id=emoji.CROSS_ID,
        callback_data=AdminProductActionCallback(
            action="delete",
            product_id=product_id,
            page=page,
            status=ProductStatus.ACTIVE.value,
        ),
    )
    add_inline_button(
        builder,
        text="Назад",
        icon_custom_emoji_id=emoji.REFRESH_ID,
        callback_data=AdminProductsPageCallback(status=ProductStatus.ACTIVE.value, page=page),
    )
    builder.adjust(1)
    return builder.as_markup()


def existing_product_preview_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_inline_button(
        builder,
        text="Сохранить изменения",
        callback_data=AdminPreviewActionCallback(action="save_bot_only"),
        style=STYLE_SUCCESS,
        icon_custom_emoji_id=emoji.CHECK_ID,
    )
    add_inline_button(
        builder,
        text=BUTTON_EDIT,
        callback_data=AdminPreviewActionCallback(action="edit"),
        style=STYLE_PRIMARY,
        icon_custom_emoji_id=emoji.REFRESH_ID,
    )
    add_inline_button(
        builder,
        text=BUTTON_CANCEL,
        callback_data=AdminPreviewActionCallback(action="cancel"),
        style=STYLE_DANGER,
        icon_custom_emoji_id=emoji.CROSS_ID,
    )
    builder.adjust(1)
    return builder.as_markup()


def store_design_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_inline_button(builder, text="Изменить цвет фона", callback_data="admin:design:color", style=STYLE_PRIMARY)
    add_inline_button(builder, text="Изменить аватар", callback_data="admin:design:avatar", style=STYLE_PRIMARY)
    add_inline_button(builder, text="Изменить обложку", callback_data="admin:design:cover", style=STYLE_PRIMARY)
    add_inline_button(builder, text="Назад", callback_data="admin:menu")
    builder.adjust(1)
    return builder.as_markup()


def delete_product_confirmation_keyboard(*, product_id: int, page: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_inline_button(
        builder,
        text="Да, удалить",
        style=STYLE_DANGER,
        callback_data=AdminProductActionCallback(
            action="delete_confirm",
            product_id=product_id,
            page=page,
            status=ProductStatus.ACTIVE.value,
        ),
    )
    add_inline_button(
        builder,
        text="Отмена",
        callback_data=AdminProductViewCallback(
            status=ProductStatus.ACTIVE.value,
            product_id=product_id,
            page=page,
        ),
    )
    builder.adjust(1)
    return builder.as_markup()


def sold_product_actions_keyboard(*, product_id: int, page: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_inline_button(
        builder,
        text=BUTTON_DELETE_FROM_LIST,
        style=STYLE_DANGER,
        icon_custom_emoji_id=emoji.CROSS_ID,
        callback_data=AdminProductActionCallback(
            action="archive",
            product_id=product_id,
            page=page,
            status=ProductStatus.SOLD.value,
        ),
    )
    add_inline_button(
        builder,
        text="Назад",
        icon_custom_emoji_id=emoji.REFRESH_ID,
        callback_data=AdminProductsPageCallback(status=ProductStatus.SOLD.value, page=page),
    )
    builder.adjust(1)
    return builder.as_markup()
