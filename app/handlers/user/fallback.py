from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.config import Settings
from app.keyboards.user import main_menu_inline_keyboard
from app.services import formatter

router = Router(name="user_fallback")


@router.message()
async def unknown_message_handler(message: Message, state: FSMContext, settings: Settings) -> None:
    user_id = message.from_user.id if message.from_user else None
    await message.answer(
        formatter.format_unknown_message(),
        parse_mode="HTML",
        reply_markup=main_menu_inline_keyboard(
            is_admin=user_id in settings.admin_ids if user_id is not None else False,
            reviews_url=settings.reviews_url,
            support_url=settings.support_url,
        ),
    )
