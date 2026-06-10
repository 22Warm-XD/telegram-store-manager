from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import Settings
from app.handlers.admin.helpers import is_admin
from app.keyboards.admin import store_design_keyboard
from app.services.store_settings_service import InvalidStoreColorError, StoreSettingsService
from app.states.product_states import ProductStates

router = Router(name="admin_store_design")


@router.callback_query(F.data == "admin:design")
async def design_menu(
    callback: CallbackQuery,
    settings: Settings,
    store_settings_service: StoreSettingsService,
) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    current = await store_settings_service.get()
    await callback.answer()
    await callback.message.answer(
        "<b>Оформление магазина</b>\n\n"
        f"Цвет фона: <code>{current.background_color}</code>\n"
        f"Аватар: {'установлен' if current.avatar_file_id else 'по умолчанию'}\n"
        f"Обложка: {'установлена' if current.cover_file_id else 'не установлена'}",
        parse_mode="HTML",
        reply_markup=store_design_keyboard(),
    )


@router.callback_query(F.data == "admin:design:color")
async def ask_color(callback: CallbackQuery, state: FSMContext, settings: Settings) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await state.set_state(ProductStates.waiting_for_store_color)
    await callback.answer()
    await callback.message.answer("Отправьте HEX-цвет: <code>505559</code> или <code>#505559</code>.", parse_mode="HTML")


@router.message(ProductStates.waiting_for_store_color)
async def save_color(
    message: Message,
    state: FSMContext,
    settings: Settings,
    store_settings_service: StoreSettingsService,
) -> None:
    if message.from_user is None or not is_admin(message.from_user.id, settings):
        return
    try:
        current = await store_settings_service.set_background_color(message.text or "")
    except InvalidStoreColorError:
        await message.answer("Нужны ровно 6 HEX-символов, например <code>505559</code>.", parse_mode="HTML")
        return
    await state.clear()
    await message.answer(f"Цвет фона обновлён: <code>{current.background_color}</code>.", parse_mode="HTML", reply_markup=store_design_keyboard())


@router.callback_query(F.data == "admin:design:avatar")
async def ask_avatar(callback: CallbackQuery, state: FSMContext, settings: Settings) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await state.set_state(ProductStates.waiting_for_store_avatar)
    await callback.answer()
    await callback.message.answer("Отправьте квадратное фото. Рекомендуемый размер: 1024×1024.")


@router.message(ProductStates.waiting_for_store_avatar, F.photo)
async def save_avatar(
    message: Message,
    state: FSMContext,
    settings: Settings,
    store_settings_service: StoreSettingsService,
) -> None:
    if message.from_user is None or not is_admin(message.from_user.id, settings):
        return
    await store_settings_service.set_avatar(message.photo[-1].file_id)
    await state.clear()
    await message.answer("Аватар магазина обновлён.", reply_markup=store_design_keyboard())


@router.callback_query(F.data == "admin:design:cover")
async def ask_cover(callback: CallbackQuery, state: FSMContext, settings: Settings) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await state.set_state(ProductStates.waiting_for_store_cover)
    await callback.answer()
    await callback.message.answer("Отправьте широкую обложку. Рекомендуемый размер: 1920×720 (соотношение 8:3).")


@router.message(ProductStates.waiting_for_store_cover, F.photo)
async def save_cover(
    message: Message,
    state: FSMContext,
    settings: Settings,
    store_settings_service: StoreSettingsService,
) -> None:
    if message.from_user is None or not is_admin(message.from_user.id, settings):
        return
    await store_settings_service.set_cover(message.photo[-1].file_id)
    await state.clear()
    await message.answer("Обложка магазина обновлена.", reply_markup=store_design_keyboard())


@router.message(ProductStates.waiting_for_store_avatar)
@router.message(ProductStates.waiting_for_store_cover)
async def design_photo_required(message: Message) -> None:
    await message.answer("Отправьте изображение именно как фото.")
