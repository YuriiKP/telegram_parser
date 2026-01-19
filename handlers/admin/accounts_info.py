import logging

from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram import F

from loader import dp, db_manage
from keyboards import admin_menu, main_admin_menu
from filters import IsAdmin, IsMainAdmin
from keyboards.text import btn_accounts_info
from storage import SystemAccountStatus


logger = logging.getLogger(__name__)


@dp.message(F.text == btn_accounts_info, IsAdmin())
async def accounts_info_command(message: Message, state: FSMContext):
    """Вывод информации о системных аккаунтах"""
    await state.clear()
    
    try:
        # Получаем все аккаунты из БД
        all_accounts = await db_manage.get_all_system_accounts()
        
        if not all_accounts:
            await message.answer(
                "⚠️ Аккаунты не найдены в базе данных.\n"
                "Используйте кнопку '🔄 Синхронизировать аккаунты' для добавления аккаунтов из папки accounts/."
            )
            return
        
        # Статистика по статусам
        status_counts = {
            SystemAccountStatus.OK: 0,
            SystemAccountStatus.IS_BUSY: 0,
            SystemAccountStatus.AUTH_REQUIRED: 0,
            SystemAccountStatus.BANNED: 0,
            SystemAccountStatus.FLOOD_WAIT: 0,
            SystemAccountStatus.SESSION_EXPIRED: 0,
        }
        
        for account in all_accounts:
            status_counts[account.status] = status_counts.get(account.status, 0) + 1
        
        # Формируем текст со статистикой
        text = (
            "<b>📊 ИНФОРМАЦИЯ О СИСТЕМНЫХ АККАУНТАХ</b>\n\n"
            f"<b>Всего аккаунтов:</b> {len(all_accounts)}\n\n"
            "<b>Статистика по статусам:</b>\n"
            f"✅ OK (свободны): {status_counts[SystemAccountStatus.OK]}\n"
            f"🔄 IS_BUSY (заняты): {status_counts[SystemAccountStatus.IS_BUSY]}\n"
            f"🔐 AUTH_REQUIRED (требуется авторизация): {status_counts[SystemAccountStatus.AUTH_REQUIRED]}\n"
            f"🚫 BANNED (забанены): {status_counts[SystemAccountStatus.BANNED]}\n"
            f"⏳ FLOOD_WAIT (флуд-ожидание): {status_counts[SystemAccountStatus.FLOOD_WAIT]}\n"
            f"📅 SESSION_EXPIRED (сессия устарела): {status_counts[SystemAccountStatus.SESSION_EXPIRED]}\n\n"
        )
        
        # Добавляем список аккаунтов (первые 10 для краткости)
        text += "<b>Список аккаунтов (первые 10):</b>\n"
        for i, account in enumerate(all_accounts[:10], 1):
            # Извлекаем номер телефона из пути сессии
            session_path = account.session
            phone = session_path.split('/')[1] if '/' in session_path else session_path
            
            # Эмодзи статуса
            status_emoji = {
                SystemAccountStatus.OK: "✅",
                SystemAccountStatus.IS_BUSY: "🔄",
                SystemAccountStatus.AUTH_REQUIRED: "🔐",
                SystemAccountStatus.BANNED: "🚫",
                SystemAccountStatus.FLOOD_WAIT: "⏳",
                SystemAccountStatus.SESSION_EXPIRED: "📅",
            }.get(account.status, "❓")
            
            text += f"{i}. {status_emoji} <code>{phone}</code> - {account.status.value}\n"
        
        if len(all_accounts) > 10:
            text += f"\n... и ещё {len(all_accounts) - 10} аккаунтов"
        
        await message.answer(text)
        
    except Exception as e:
        await message.answer('❌ Ошибка при получении информации об аккаунтах')
        logger.error(f'Ошибка при получении информации об аккаунтах:\n{str(e)}')