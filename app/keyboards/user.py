from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.constants import (
    MAIN_MENU_ADMIN,
    MAIN_MENU_CATALOG,
    MAIN_MENU_REVIEWS,
    MAIN_MENU_STORE,
    MAIN_MENU_SUPPORT,
)
from app.keyboards.styles import STYLE_PRIMARY, STYLE_SUCCESS, add_inline_button, styled_keyboard_button
from app.utils import premium_emoji as emoji


def _can_use_web_app(url: str | None) -> bool:
    return bool(url and url.lower().startswith("https://"))


def main_menu_keyboard(
    *,
    is_admin: bool = False,
    mini_app_url: str | None = None,
) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    if _can_use_web_app(mini_app_url):
        builder.row(
            styled_keyboard_button(
                text=MAIN_MENU_STORE,
                style=STYLE_SUCCESS,
                icon_custom_emoji_id=emoji.SHOP_ID,
                web_app=WebAppInfo(url=mini_app_url),
            )
        )
    builder.row(
        styled_keyboard_button(
            text=MAIN_MENU_CATALOG,
            style=STYLE_SUCCESS,
            icon_custom_emoji_id=emoji.SHOP_ID,
        )
    )
    builder.row(
        styled_keyboard_button(
            text=MAIN_MENU_REVIEWS,
            style=STYLE_PRIMARY,
            icon_custom_emoji_id=emoji.SHIELD_ID,
        ),
        styled_keyboard_button(
            text=MAIN_MENU_SUPPORT,
            style=STYLE_PRIMARY,
            icon_custom_emoji_id=emoji.USER_ID,
        ),
    )
    if is_admin:
        builder.row(styled_keyboard_button(text=MAIN_MENU_ADMIN, icon_custom_emoji_id=emoji.REFRESH_ID))
    return builder.as_markup(resize_keyboard=True, input_field_placeholder="Выберите действие")


def main_menu_inline_keyboard(
    *,
    is_admin: bool = False,
    reviews_url: str,
    support_url: str,
    mini_app_url: str | None = None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if mini_app_url:
        if _can_use_web_app(mini_app_url):
            add_inline_button(
                builder,
                text=MAIN_MENU_STORE,
                web_app=WebAppInfo(url=mini_app_url),
                style=STYLE_SUCCESS,
                icon_custom_emoji_id=emoji.SHOP_ID,
            )
        else:
            add_inline_button(
                builder,
                text=MAIN_MENU_STORE,
                url=mini_app_url,
                style=STYLE_SUCCESS,
                icon_custom_emoji_id=emoji.SHOP_ID,
            )
    add_inline_button(
        builder,
        text=MAIN_MENU_CATALOG,
        callback_data="main:catalog",
        style=STYLE_SUCCESS,
        icon_custom_emoji_id=emoji.SHOP_ID,
    )
    add_inline_button(
        builder,
        text=MAIN_MENU_REVIEWS,
        url=reviews_url,
        style=STYLE_PRIMARY,
        icon_custom_emoji_id=emoji.SHIELD_ID,
    )
    add_inline_button(
        builder,
        text=MAIN_MENU_SUPPORT,
        url=support_url,
        style=STYLE_PRIMARY,
        icon_custom_emoji_id=emoji.USER_ID,
    )
    if is_admin:
        add_inline_button(
            builder,
            text=MAIN_MENU_ADMIN,
            callback_data="main:admin",
            icon_custom_emoji_id=emoji.REFRESH_ID,
        )
        if mini_app_url:
            builder.adjust(1, 1, 2, 1)
        else:
            builder.adjust(1, 2, 1)
    else:
        if mini_app_url:
            builder.adjust(1, 1, 2)
        else:
            builder.adjust(1, 2)
    return builder.as_markup()


def url_button_keyboard(*, text: str, url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    add_inline_button(builder, text=text, url=url, style=STYLE_PRIMARY)
    return builder.as_markup()
