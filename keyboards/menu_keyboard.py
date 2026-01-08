from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime

from keyboards.text import *


# Админ клавиатуры 
admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=btn_admins), KeyboardButton(text=btn_about_users_bot)],
        [KeyboardButton(text=btn_sync_accounts)]
    ],
    resize_keyboard=True
)

main_admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=btn_admins), KeyboardButton(text=btn_about_users_bot)],
        [KeyboardButton(text=btn_sync_accounts)]
    ],
    resize_keyboard=True
)



# Юзер клавиатуры
def user_main_menu(user=None):
    builder = InlineKeyboardBuilder()
    
    builder.button(text=btn_parse, callback_data='btn_parse')
    builder.button(text=btn_status, callback_data='btn_status')
    
    # Проверяем наличие активной подписки
    has_active_subscription = False
    if user and user.subscription_end:
        now = datetime.now()
        if user.subscription_end >= now:
            has_active_subscription = True
    
    if has_active_subscription:
        builder.button(text=btn_profile, callback_data='btn_profile')
    else:
        builder.button(text=btn_subscription, callback_data='btn_subscription')
    
    builder.button(text=btn_help, callback_data='btn_help')

    builder.adjust(1, 1, 2)
    return builder.as_markup()


def user_parsing_started():
    builder = InlineKeyboardBuilder()
    
    builder.button(text=btn_status, callback_data='btn_status')
    builder.button(text=btn_help, callback_data='btn_help')

    builder.adjust(1)
    return builder.as_markup()



def user_buy_menu():
    builder = InlineKeyboardBuilder()
    
    builder.button(text=btn_buy_one_month, callback_data='btn_buy_one_month')
    builder.button(text=btn_main_menu, callback_data='btn_main_menu')

    builder.adjust(1)
    return builder.as_markup()


def user_help_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text=btn_main_menu, callback_data='btn_main_menu')
    builder.adjust(1)
    
    return builder.as_markup()
