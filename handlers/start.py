from aiogram.types import Message, CallbackQuery, BotCommandScopeDefault
from aiogram.filters import CommandStart, CommandObject
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram import F

from loader import dp, bot, deep_links_admin_manage
from loader import db_manage
from keyboards import *
from filters import IsAdmin, IsMainAdmin, IsUser

from commands import user_commands
    


# Старт с диплинком
@dp.message(CommandStart(deep_link=True))
async def process_start_bot_deep_link(message: Message, state: FSMContext, command: CommandObject):    
    await state.clear()

    args = command.args
    
    if args in deep_links_admin_manage:
        status_user = deep_links_admin_manage[args]
        del deep_links_admin_manage[args]

        await db_manage.update_user(
            user_id=message.from_user.id,
            status_user=status_user
        )

        await message.answer(
            text=f'Поздравляю! Теперь ты {status_user}'
        )

        await process_start_bot(message, message.from_user.id, message.from_user.first_name)
    
    else:
        await process_start_bot(message, message.from_user.id, message.from_user.first_name)



# Обычный старт 
@dp.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    await state.clear()
    
    await db_manage.add_new_user(
        message.from_user.id, 
        message.from_user.username, 
        message.from_user.first_name, 
        message.from_user.last_name
        )
    
    await process_start_bot(message, message.from_user.id, message.from_user.first_name)


# Старт с колбэка
@dp.callback_query(F.data == 'btn_main_menu')
async def inline_process_start_bot(query: CallbackQuery, state: FSMContext):
    await state.clear()
    
    await state.clear()
    await process_start_bot(query.message, query.from_user.id, query.from_user.first_name)



# Функция запуска
async def process_start_bot(message: Message, user_id, first_name):
    user = await db_manage.get_user_by_id(user_id)
    
    await bot.set_my_commands(
        commands=user_commands,
        scope=BotCommandScopeDefault()
        )

    menu_keyboards = {
        'admin': admin_menu,
        'main_admin': main_admin_menu
    }


    # Определяем клавиатуру и текст
    if user.status_user in ('admin', 'main_admin') and message.text == '/start':
        keyboard = menu_keyboards[user.status_user]
        
        await message.answer(
            text=admin_main_menu_text,
            reply_markup=keyboard
        )


    try:
        await message.edit_text(
            text=user_start_message(message.from_user.first_name),
            reply_markup=user_main_menu()
        )
    except TelegramBadRequest:
        await message.answer(
            text=user_start_message(message.from_user.first_name),
            reply_markup=user_main_menu()
        )
        try:
            if message.text != '/start':
                await message.delete()
        except TelegramBadRequest:
            pass  # Игнорируем, если уже удалено