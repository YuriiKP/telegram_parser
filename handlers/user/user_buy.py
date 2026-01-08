from datetime import datetime, timedelta
from aiogram.types import CallbackQuery, Message, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram import F

from loader import dp, db_manage, YOO_KASSA_PROVIDER_TOKEN
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
    
    # Показываем меню выбора способа оплаты
    try:
        await query.message.edit_text(
            text=payment_method_text,
            reply_markup=user_payment_method_menu()
        )
    except TelegramBadRequest:
        # Если нельзя редактировать, отправляем новое сообщение и удаляем старое
        await query.message.answer(
            text=payment_method_text,
            reply_markup=user_payment_method_menu()
        )
        try:
            await query.message.delete()
        except TelegramBadRequest:
            pass  # Игнорируем, если уже удалено


@dp.callback_query(F.data == 'btn_pay_with_card')
async def pay_with_card_handler(query: CallbackQuery, state: FSMContext):
    await state.clear()
    
    # Цена в копейках (2 рубля = 200 копеек)
    prices = [LabeledPrice(label="Доступ к парсеру на 1 месяц", amount=59000)]
    
    # provider_data для ЮKassa с указанием метода оплаты СБП
    # provider_data = '{"payment_method_type": "sbp"}'
    
    # Отправляем инвойс с провайдером ЮKassa
    await query.message.answer_invoice(
        title="Подписка на 1 месяц",
        description="Вы получаете полный доступ к парсеру",
        prices=prices,
        payload="one_month",         # id тарифа
        currency="RUB",              # Код валюты для рублёвых платежей
        provider_token=YOO_KASSA_PROVIDER_TOKEN,
        # provider_data=provider_data,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Оплатить 590 ₽", pay=True)],
            [InlineKeyboardButton(text="Отмена", callback_data="btn_buy")]
        ])
    )
    
    await query.message.delete()


@dp.callback_query(F.data == 'btn_pay_with_stars')
async def pay_with_stars_handler(query: CallbackQuery, state: FSMContext):
    await state.clear()
    
    # Цена в звездах (1 звезда)
    prices = [LabeledPrice(label="Доступ к парсеру на 1 месяц", amount=329)]
    
    # Отправляем инвойс для Telegram Stars
    await query.message.answer_invoice(
        title="Подписка на 1 месяц",
        description="Вы получаете полный доступ к парсеру",
        prices=prices,
        payload="one_month",         # id тарифа
        currency="XTR",              # Код валюты для Telegram Stars
        provider_token='',           # Для Stars передаем пустую строку
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Оплатить 329 ⭐️", pay=True)],
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
        
        # Продление подписки на 30 дней
        user = await db_manage.get_user_by_id(user_id)
        now = datetime.now()
        if user.subscription_end and user.subscription_end > now:
            # Если подписка активна, продлеваем от текущей даты окончания
            new_end = user.subscription_end + timedelta(days=30)
        else:
            # Иначе устанавливаем подписку от текущего момента
            new_end = now + timedelta(days=30)
        
        await db_manage.update_user(user_id, subscription_end=new_end)
        # Меняю в объекте, чтобы получить нужное меню после оплаты
        user.subscription_end = new_end

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
            text=user_start_message(),
            reply_markup=user_main_menu(user)
        )