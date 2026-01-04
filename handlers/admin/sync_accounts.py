import logging

from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram import F

from loader import dp, db_manage
from keyboards import admin_menu, main_admin_menu
from filters import IsAdmin, IsMainAdmin
from keyboards.text import btn_sync_accounts



logger = logging.getLogger(__name__)

@dp.message(F.text == btn_sync_accounts, IsAdmin())
async def sync_accounts_command(message: Message, state: FSMContext):
    """Синхронизация аккаунтов из папки accounts/"""
    await state.clear()
    
    try:
        # Вызываем метод scan_accounts из db_manage
        accounts_added = await db_manage.scan_accounts()
        
        if accounts_added:
            await message.answer(
                f"✅ Синхронизация аккаунтов завершена!\n"
                f"Добавлено аккаунтов: {len(accounts_added)}\n"
                f"ID добавленных аккаунтов: {', '.join(map(str, accounts_added))}"
            )
        else:
            # Получаем все аккаунты для информации
            all_accounts = await db_manage.get_all_system_accounts()
            if all_accounts:
                await message.answer(
                    f"ℹ️ Новых аккаунтов не найдено.\n"
                    f"Всего аккаунтов в базе: {len(all_accounts)}\n"
                    f"Папка accounts/ уже синхронизирована."
                )
            else:
                await message.answer(
                    "⚠️ Аккаунты не найдены!\n"
                    "Проверьте папку accounts/ на наличие файлов сессий.\n"
                    "Формат: accounts/+79123456789/\n"
                    "  - session.session\n"
                    "  - session.json"
                )
                
    except Exception as e:
        await message.answer('Ошибка синхронизации аккаунтов')
        logger.error(f'Ошибка при синхронизации аккаунтов:\n{str(e)}')
    
    # Возвращаем админское меню
    user = await db_manage.get_user_by_id(message.from_user.id)
    if user and user.status_user == 'main_admin':
        await message.answer(
            "Админ меню",
            reply_markup=main_admin_menu
        )
    else:
        await message.answer(
            "Админ меню",
            reply_markup=admin_menu
        )
