from aiogram.types import CallbackQuery, Message, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram import F

from loader import dp, db_manage
from keyboards import *


# Обработчик кнопки "Купить"
@dp.callback_query(F.data == 'btn_buy')
async def buy_handler(query: CallbackQuery, state: FSMContext):
    await state.clear()

    try:
        await query.message.edit_text(
            text=user_buy_text,
            reply_markup=user_buy_menu()
        )
    except TelegramBadRequest:
        # Если нельзя редактировать, отправляем новое сообщение и удаляем старое
        await query.message.answer(
            text=user_buy_text,
            reply_markup=user_buy_menu()
        )
        try:
            await query.message.delete()
        except TelegramBadRequest:
            pass  # Игнорируем, если уже удалено


@dp.callback_query(F.data == 'btn_buy_one_month')
async def buy_one_month_handler(query: CallbackQuery, state: FSMContext):
    await state.clear()
    
    # 1. Формируем цену
    prices = [LabeledPrice(label="1 месяц VPN", amount=1)] 

    # 2. Отправляем инвойс
    await query.message.answer_invoice(
        title="Подписка на 1 месяц",
        description="ЖКХ подписка на 30 дней",
        prices=prices,
        payload="one_month",         # id тарифа
        currency="XTR",              # Код валюты для звезд тг
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Оплатить 1 ⭐️ | 2₽", pay=True)],
            [InlineKeyboardButton(text="Отмена", callback_data="btn_buy")]
        ])
    )

    await query.message.delete()


# Обработака успешной оплаты
@dp.message(F.successful_payment)
async def success_payment_handler(message: Message):
    payment_info = message.successful_payment
    
    if payment_info.invoice_payload == "one_month":
        user_id = message.from_user.id
        
        #
        # Здесь кака-то логика с заказом
        #

        # Сохраняем информацию о платеже в базе данных
        await db_manage.add_payment(
            user_id=user_id,
            amount=payment_info.total_amount,
            currency=payment_info.currency,
            payload=payment_info.invoice_payload,
            telegram_payment_charge_id=payment_info.telegram_payment_charge_id,
            provider_payment_charge_id=payment_info.provider_payment_charge_id,
            status='completed'
        )

        await message.answer("Оплата прошла успешно! Ваша подписка обновлена. 🚀")
        await message.answer(
            text='Забирай мешок картошки',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=
                    [
                        [InlineKeyboardButton(text=btn_main_menu, callback_data='btn_main_menu')],
                    ]
                )
            )