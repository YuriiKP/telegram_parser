from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime

from keyboards.text import *
from storage import User


# Админ клавиатуры
admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=btn_admins), KeyboardButton(text=btn_about_users_bot)],
        [KeyboardButton(text=btn_sync_accounts)],
        [KeyboardButton(text=btn_accounts_info)]
    ],
    resize_keyboard=True
)

main_admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=btn_admins), KeyboardButton(text=btn_about_users_bot)],
        [KeyboardButton(text=btn_sync_accounts)],
        [KeyboardButton(text=btn_accounts_info)]
    ],
    resize_keyboard=True
)



# Юзер клавиатуры
def user_main_menu(user: User = None):
    # Проверяем наличие активной подписки
    has_active_subscription = False
    if user and user.subscription_end:
        now = datetime.now()
        if user.subscription_end >= now:
            has_active_subscription = True

    builder = InlineKeyboardBuilder()
    
    if has_active_subscription:
        builder.button(text=btn_parse, callback_data='btn_parse')
        builder.button(text=btn_status, callback_data='btn_status')
        builder.button(text=btn_profile, callback_data='btn_profile')
    else:
        builder.button(text=btn_buy, callback_data='btn_buy')
        builder.button(text=btn_parse, callback_data='btn_parse')
        builder.button(text=btn_status, callback_data='btn_status')    

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


def user_payment_method_menu():
    """Меню выбора способа оплаты (карта или звезды)."""
    builder = InlineKeyboardBuilder()
    
    builder.button(text=btn_pay_with_card, callback_data='btn_pay_with_card')
    builder.button(text=btn_pay_with_stars, callback_data='btn_pay_with_stars')
    builder.button(text=btn_back, callback_data='btn_buy')

    builder.adjust(1)
    return builder.as_markup()


def user_help_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text=btn_main_menu, callback_data='btn_main_menu')
    builder.adjust(1)
    
    return builder.as_markup()
