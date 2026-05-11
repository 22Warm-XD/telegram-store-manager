from __future__ import annotations

from typing import Any

from aiogram.types import InlineKeyboardButton, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


STYLE_PRIMARY = "primary"
STYLE_SUCCESS = "success"
STYLE_DANGER = "danger"


def add_inline_button(
    builder: InlineKeyboardBuilder,
    *,
    text: str,
    style: str | None = None,
    icon_custom_emoji_id: str | None = None,
    **kwargs: Any,
) -> None:
    extra: dict[str, str] = {}
    if style:
        extra["style"] = style
    if icon_custom_emoji_id:
        extra["icon_custom_emoji_id"] = icon_custom_emoji_id
    builder.button(text=text, **kwargs, **extra)


def styled_keyboard_button(
    *,
    text: str,
    style: str | None = None,
    icon_custom_emoji_id: str | None = None,
    **kwargs: Any,
) -> KeyboardButton:
    extra: dict[str, str] = {}
    if style:
        extra["style"] = style
    if icon_custom_emoji_id:
        extra["icon_custom_emoji_id"] = icon_custom_emoji_id
    return KeyboardButton(text=text, **kwargs, **extra)


def styled_inline_button(
    *,
    text: str,
    style: str | None = None,
    icon_custom_emoji_id: str | None = None,
    **kwargs: Any,
) -> InlineKeyboardButton:
    extra: dict[str, str] = {}
    if style:
        extra["style"] = style
    if icon_custom_emoji_id:
        extra["icon_custom_emoji_id"] = icon_custom_emoji_id
    return InlineKeyboardButton(text=text, **kwargs, **extra)
