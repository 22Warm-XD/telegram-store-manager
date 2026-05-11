from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from app.config import Settings
from app.constants import MAIN_MENU_ADMIN
from app.handlers.admin.helpers import is_admin
from app.keyboards.admin import admin_menu_keyboard
from app.services import formatter
from app.services.product_service import ProductService

router = Router(name="admin_panel")


@router.message(Command("admin"))
@router.message(F.text == MAIN_MENU_ADMIN)
async def admin_panel_handler(
    message: Message,
    settings: Settings,
    state: FSMContext,
    product_service: ProductService,
) -> None:
    if message.from_user is None or not is_admin(message.from_user.id, settings):
        await message.answer(formatter.format_no_access_message())
        return

    await state.clear()
    await product_service.record_admin_action(admin_id=message.from_user.id, action="OPEN_ADMIN_PANEL")
    await message.answer(
        formatter.format_admin_menu_message(),
        parse_mode="HTML",
        reply_markup=admin_menu_keyboard(),
    )
    try:
        cleanup_message = await message.answer("Админ-панель открыта.", reply_markup=ReplyKeyboardRemove())
        await cleanup_message.delete()
    except TelegramAPIError:
        pass


@router.callback_query(F.data == "admin:menu")
@router.callback_query(F.data == "main:admin")
async def admin_menu_callback(callback: CallbackQuery, settings: Settings) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer(formatter.format_no_access_message(), show_alert=True)
        return

    await callback.answer()
    try:
        await callback.message.edit_text(
            formatter.format_admin_menu_message(),
            parse_mode="HTML",
            reply_markup=admin_menu_keyboard(),
        )
    except Exception:
        await callback.message.answer(
            formatter.format_admin_menu_message(),
            parse_mode="HTML",
            reply_markup=admin_menu_keyboard(),
        )


@router.callback_query(F.data == "admin:noop")
async def admin_noop_callback(callback: CallbackQuery) -> None:
    await callback.answer()
