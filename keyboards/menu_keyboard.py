from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.text import *


# Админ клавиатуры 
admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=btn_admins), KeyboardButton(text=btn_about_users_bot)]
    ],
    resize_keyboard=True
)

main_admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=btn_admins), KeyboardButton(text=btn_about_users_bot)]
    ],
    resize_keyboard=True
)



# Юзер клавиатуры
def user_main_menu():
    builder = InlineKeyboardBuilder()
    
    builder.button(text=btn_buy, callback_data='btn_buy')
    builder.button(text=btn_help, callback_data='btn_help')

    builder.adjust(1)
    return builder.as_markup()


def user_buy_menu():
    builder = InlineKeyboardBuilder()
    
    builder.button(text=btn_buy, callback_data='btn_buy_one_month')
    builder.button(text=btn_main_menu, callback_data='btn_main_menu')

    builder.adjust(1)
    return builder.as_markup()


def user_help_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text=btn_main_menu, callback_data='btn_main_menu')
    builder.adjust(1)
    
    return builder.as_markup()