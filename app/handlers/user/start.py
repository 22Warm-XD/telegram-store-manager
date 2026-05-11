from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LinkPreviewOptions, Message, ReplyKeyboardRemove

from app.config import Settings
from app.constants import MAIN_MENU_BACK
from app.keyboards.user import main_menu_inline_keyboard
from app.services import formatter

router = Router(name="user_start")
MAIN_MESSAGE_ID_KEY = "main_message_id"


@router.message(Command("id"))
async def user_id_handler(message: Message) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить Telegram ID.")
        return
    await message.answer(f"Ваш Telegram ID: <code>{message.from_user.id}</code>", parse_mode="HTML")


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext, settings: Settings) -> None:
    await _remove_reply_keyboard(message)
    await _delete_previous_main_message(message, state)
    user_id = message.from_user.id if message.from_user else None
    sent_message = await message.answer(
        formatter.format_start_message(message.from_user.first_name if message.from_user else "друг", settings.tiktok_url),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(is_disabled=True),
        reply_markup=main_menu_inline_keyboard(
            is_admin=user_id in settings.admin_ids if user_id is not None else False,
            reviews_url=settings.reviews_url,
            support_url=settings.support_url,
            mini_app_url=settings.mini_app_url,
        ),
    )
    await state.update_data(**{MAIN_MESSAGE_ID_KEY: sent_message.message_id})


@router.callback_query(F.data == "main:home")
async def main_home_handler(callback: CallbackQuery, state: FSMContext, settings: Settings) -> None:
    user_id = callback.from_user.id if callback.from_user else None
    await callback.answer()
    await callback.message.edit_text(
        formatter.format_start_message(callback.from_user.first_name if callback.from_user else "друг", settings.tiktok_url),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(is_disabled=True),
        reply_markup=main_menu_inline_keyboard(
            is_admin=user_id in settings.admin_ids if user_id is not None else False,
            reviews_url=settings.reviews_url,
            support_url=settings.support_url,
            mini_app_url=settings.mini_app_url,
        ),
    )
    await state.update_data(**{MAIN_MESSAGE_ID_KEY: callback.message.message_id})


@router.message(F.text == MAIN_MENU_BACK)
async def back_to_main_menu_handler(message: Message, state: FSMContext, settings: Settings) -> None:
    await state.clear()
    await _remove_reply_keyboard(message)
    user_id = message.from_user.id if message.from_user else None
    sent_message = await message.answer(
        formatter.format_start_message(message.from_user.first_name if message.from_user else "друг", settings.tiktok_url),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(is_disabled=True),
        reply_markup=main_menu_inline_keyboard(
            is_admin=user_id in settings.admin_ids if user_id is not None else False,
            reviews_url=settings.reviews_url,
            support_url=settings.support_url,
            mini_app_url=settings.mini_app_url,
        ),
    )
    await state.update_data(**{MAIN_MESSAGE_ID_KEY: sent_message.message_id})


async def _remove_reply_keyboard(message: Message) -> None:
    try:
        sent_message = await message.answer("Меню обновлено.", reply_markup=ReplyKeyboardRemove())
        await sent_message.delete()
    except TelegramAPIError:
        return


async def _delete_previous_main_message(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    message_id = data.get(MAIN_MESSAGE_ID_KEY)
    if not message_id:
        return
    try:
        await message.bot.delete_message(chat_id=message.chat.id, message_id=int(message_id))
    except (TelegramAPIError, TypeError, ValueError):
        return
