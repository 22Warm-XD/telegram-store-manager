from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from app.config import Settings
from app.constants import MAIN_MENU_REVIEWS, MAIN_MENU_SUPPORT
from app.keyboards.user import url_button_keyboard
from app.services import formatter

router = Router(name="user_support")


@router.message(F.text == MAIN_MENU_REVIEWS)
async def reviews_handler(message: Message, settings: Settings) -> None:
    await message.answer(
        formatter.format_reviews_message(),
        parse_mode="HTML",
        reply_markup=url_button_keyboard(text="Открыть отзывы", url=settings.reviews_url),
    )


@router.message(F.text == MAIN_MENU_SUPPORT)
async def support_handler(message: Message, settings: Settings) -> None:
    await message.answer(
        formatter.format_support_link_message(),
        parse_mode="HTML",
        reply_markup=url_button_keyboard(text="Написать в поддержку", url=settings.support_url),
    )
