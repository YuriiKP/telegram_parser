from aiogram.types import Message, CallbackQuery, LinkPreviewOptions
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
from aiogram import F

from loader import dp
from keyboards import *



@dp.message(Command('help'))
async def help_command(message: Message, state: FSMContext):
    await state.clear()
    await process_help(message)


@dp.callback_query(F.data == 'btn_help')
async def help_query(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await process_help(query.message)


async def process_help(message: Message):
    try:
        await message.edit_text(
            text=user_help_text,
            reply_markup=user_help_menu()
        )
    except TelegramBadRequest:
        await message.answer(
            text=user_help_text,
            reply_markup=user_help_menu()
        )
        try:
            if message.text != '/help':
                await message.delete()
        except TelegramBadRequest:
            pass  # Игнорируем, если уже удалено
