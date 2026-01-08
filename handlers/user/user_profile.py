from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram import F
from aiogram.utils.keyboard import InlineKeyboardBuilder

from loader import dp, db_manage
from keyboards import *


@dp.callback_query(F.data == 'btn_profile')
async def profile_handler(query: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки 'Профиль'"""
    await state.clear()
    
    # Получаем данные пользователя
    user = await db_manage.get_user_by_id(query.from_user.id)
    if not user:
        await query.answer("Пользователь не найден", show_alert=True)
        return
    
    # Формируем текст профиля
    profile_text = user_profile_text(user)
    
    # Создаем клавиатуру с кнопкой "Назад" или "Главное меню"
    builder = InlineKeyboardBuilder()
    builder.button(text=btn_main_menu, callback_data='btn_main_menu')
    builder.adjust(1)
    
    try:
        await query.message.edit_text(
            text=profile_text,
            reply_markup=builder.as_markup()
        )
    except TelegramBadRequest:
        # Если нельзя редактировать, отправляем новое сообщение и удаляем старое
        await query.message.answer(
            text=profile_text,
            reply_markup=builder.as_markup()
        )
        try:
            await query.message.delete()
        except TelegramBadRequest:
            pass  # Игнорируем, если уже удалено