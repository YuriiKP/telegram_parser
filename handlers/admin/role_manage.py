from random import randint

from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.deep_linking import create_start_link
from aiogram import F

from loader import dp, bot, TG_ADMIN, deep_links_admin_manage, symbols
from loader import db_manage
from keyboards import *
from filters import IsAdmin, IsMainAdmin
from utils import State_Ban_Admin
from utils import CB_ModerAdmins


################################################################################
# Управление админами
@dp.message(F.text == btn_admins, IsMainAdmin())
async def admin_manage_menu(message: Message, state: FSMContext):
    await state.clear()

    admins = await db_manage.get_admins()

    text = '<b>ВСЕ АДМИНИСТРАТОРЫ</b>'
    for admin in admins:
        if int(admin.user_id) == int(TG_ADMIN):
            pass
        else:
            text += f'\n\n{admin.username} <a href="tg://user?id={admin.user_id}">{admin.first_name}</a> ID: <code>{admin.user_id}</code>'

    await message.answer(
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='🛠 Добавить админа', callback_data='add_admin')],
            [InlineKeyboardButton(text='🗑 Разжаловать', callback_data='ban_admin')],
        ])
    )

# Кого добавить
@dp.callback_query(F.data == 'add_admin', IsMainAdmin())
async def choice_add_admin(query: CallbackQuery, state: FSMContext):
    await query.message.answer(
        text='Кого добавляем?',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Главного админа', callback_data=CB_ModerAdmins(action='add_admin', status_user='main_admin').pack())],
            [InlineKeyboardButton(text='Админа', callback_data=CB_ModerAdmins(action='add_admin', status_user='admin').pack())],
        ])
    )

# Создание ссылки
@dp.callback_query(CB_ModerAdmins.filter(F.action == 'add_admin'), IsMainAdmin())
async def prpcess_add_admin(query: CallbackQuery, state: FSMContext, callback_data: CB_ModerAdmins):
    status_user = callback_data.status_user
    
    str_link = ''
    for _ in range(5):
        str_link += symbols[randint(0, 35)]
        
    start_link = await create_start_link(
        bot = bot,
        payload=str_link
    )
    
    deep_links_admin_manage[str_link] = status_user

    await query.message.answer(
        text=start_link
    )


# Удаление админа
@dp.callback_query(F.data == 'ban_admin', IsMainAdmin())
async def process_ban_admin(query: CallbackQuery, state: FSMContext):
    await state.set_state(State_Ban_Admin.msg)

    await query.message.answer(
        text='Отправьте id пользователя'
    )

# Полчение ид пользователя
@dp.message(State_Ban_Admin.msg, IsMainAdmin())
async def ban_admin(message: Message, state: FSMContext):   
    try:
        user_id = int(message.text)
        
        await db_manage.update_user(
            user_id=user_id,
            status_user='user'
        )

        await message.answer(
            text=f'Пользователь {message.text} удален из админов'
        )

        await state.clear()
    
    except TypeError and ValueError:
        await message.answer(
            text=f'Такого пользователя нет, отправьте id заново'
        )