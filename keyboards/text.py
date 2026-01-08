from datetime import datetime



# Кнопки админов
btn_admins = '🔑 Админы'
btn_about_users_bot = '👥 Пользователи'
btn_sync_accounts = '🔄 Синхронизировать аккаунты'

# Текст админов
admin_main_menu_text = 'Админ меню'




# Кнопки юзеров
btn_main_menu = '🏠 Главное меню'

btn_buy = '💳 Купить'
btn_subscription = '💎 Подписка'
btn_profile = '👤 Профиль'
btn_buy_one_month = '🟢 1 месяц'
btn_pay_with_card = '💳 Картой РФ'
btn_pay_with_stars = '⭐️ Звездами'
btn_help = '🆘 Помощь'
btn_parse = '🔍 Парсинг'
btn_status = '📊 Статус задач'
btn_cancel_task = '❌ Отменить задачу'
btn_back = '👈 Назад'
btn_only_active = '🎯 Только активных'


# Текст юзеров
def user_start_message():
    return (
        '<b>Это бот для нализа Telegram чатов и каналов.</b>\n\n'
        '<b>Основные функции:</b>\n'
        '🔍 Парсинг участников чатов, активных участников, историю чатов\n'
        '📊 Отслеживание статуса задач\n'
        '📁 Получение результатов в Excel и TXT форматах\n\n'
        '<i>Открыт к предложениям и пожеланиям! Если у вас есть идеи по улучшению '
        'бота или новые функции, которые хотели бы видеть - пишите @foteleg_b. Постараюсь реализовать их в боте.</i>'
    )

user_buy_text = (
    '<b>Доступные подписки</b>\n\n'
    '<b>Месяц</b>\n'
    '    • 590 ₽\n'
    '    • 30 дней доступа\n'
    '    • Все функции'
)

payment_method_text = (
    '<b>Выберите способ оплаты</b>\n\n'
    '💳 <b>Картой РФ</b> – оплата через ЮKassa\n'
    '⭐️ <b>Звездами</b> – оплата через Telegram Stars'
)


user_help_text = '''
🆘 В этом разделе доступно:

Решение проблем: Помощь, если возникли сложности.

Поддержка: Прямая связь с администратором @foteleg_b. Пишите, разберемся.

Открыт к предложениям и пожеланиям! Если у вас есть идеи по улучшению бота
или новые функции, которые хотели бы видеть - сообщите. Постараюсь реализовать их в боте.
'''


def user_profile_text(user):
    """Формирует текст профиля пользователя."""    
    user_id = user.user_id
    subscription_end = user.subscription_end
    
    if subscription_end is None:
        subscription_info = "❌ Подписка отсутствует"
    else:
        now = datetime.now()
        if subscription_end >= now:
            # активная подписка
            remaining = subscription_end - now
            days = remaining.days
            hours = remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60
            subscription_info = (
                f"✅ Подписка активна до {subscription_end.strftime('%Y.%m.%d. %H:%M')}\n"
                f"  • Осталось: {days} дн., {hours} ч., {minutes} мин."
            )
        else:
            subscription_info = f"❌ Подписка истекла {subscription_end.strftime('%d.%m.%Y %H:%M')}"
    
    return (
        f"👤 <b>Профиль пользователя</b>\n\n"
        f"🆔 ID: {user_id}\n"
        f"📅 Дата регистрации: {user.reg_time.strftime('%d.%m.%Y %H:%M') if user.reg_time else 'неизвестно'}\n"
        f"{subscription_info}"
    )
