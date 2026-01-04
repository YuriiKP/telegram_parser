import re
import logging

from aiogram.types import Message, CallbackQuery, LinkPreviewOptions
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram import F
from aiogram.exceptions import TelegramBadRequest

from loader import dp, bot, db_manage
from keyboards import user_main_menu
from storage import ParsingTaskStatus
from utils.states import State_Parsing



logger = logging.getLogger(__name__)

@dp.message(Command('cancel'))
async def cancel_command(message: Message, state: FSMContext):
    """Обработка команды /cancel - отмена текущего действия"""
    current_state = await state.get_state()
    
    if current_state is None:
        await message.answer("Нет активных действий для отмены.")
        return
    
    # Проверяем, находится ли пользователь в состоянии парсинга
    if current_state == State_Parsing.waiting_for_link:
        await state.clear()
        await message.answer(
            "❌ Парсинг отменен.\n"
            "Вы можете начать заново, нажав кнопку 'Парсинг'.",
            reply_markup=user_main_menu()
        )
    else:
        await state.clear()
        await message.answer("Действие отменено.")


# Обработчики инлайн кнопок
@dp.callback_query(F.data == 'btn_parse')
async def inline_parse_command(query: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки 'Парсинг' - запуск процесса парсинга"""
    await query.answer()
    
    # Устанавливаем состояние ожидания ссылки
    await state.set_state(State_Parsing.waiting_for_link)
    
    await query.message.edit_text(
        "🔍 <b>Парсинг чата/канала</b>\n\n"
        "Отправьте ссылку на чат или канал в любом формате:\n"
        "• https://t.me/chat_name\n"
        "• @chat_name\n"
        "• t.me/chat_name\n\n"
        "<i>Требуется активная подписка.</i>\n\n"
        "<b>Для отмены отправьте /cancel</b>",
        reply_markup=user_main_menu()
    )


@dp.message(State_Parsing.waiting_for_link)
async def process_parsing_link(message: Message, state: FSMContext):
    """Обработка ссылки на парсинг, отправленной пользователем"""
    link = message.text.strip()
    
    # Очищаем состояние
    await state.clear()
    
    # Валидация ссылки
    if not link:
        await message.answer(
            "❌ Ссылка не может быть пустой.\n"
            "Пожалуйста, отправьте ссылку на Telegram чат/канал."
        )
        return
    
    # Проверяем, что ссылка на Telegram
    telegram_pattern = r'^(https?://)?(t\.me/|telegram\.me/)(\+[a-zA-Z0-9_-]+|[a-zA-Z0-9_]+)(/[0-9]+)?$'
    if not re.match(telegram_pattern, link):
        await message.answer(
            "❌ Некорректная ссылка. Используйте ссылку на Telegram чат/канал.\n"
            "Примеры:\n"
            "• https://t.me/chat_name\n"
            "• @chat_name\n"
            "• t.me/chat_name"
        )
        return
    
    # Создаем задачу парсинга
    try:
        task_id = await db_manage.create_parsing_task(
            creator_id=message.from_user.id,
            target_url=link
        )
        
        await message.answer(
            f"✅ <b>Задача парсинга создана!</b>\n\n"
            f"<b>ID задачи:</b> {task_id}\n"
            f"<b>Ссылка:</b> {link}\n\n"
            f"Статус можно проверить кнопкой <b>\"Статус задач\"</b> или командой /status\n"
            f"Ожидайте уведомления о завершении.",
            reply_markup=user_main_menu(),
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
        
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при создании задачи:\n"
            f"Попробуйте позже или обратитесь в поддержку.",
            reply_markup=user_main_menu()
        )
        logger.error(f"Ошибка при создании задачи: {str(e)}")



# ==================== Получение статуса задачи ====================
@dp.message(Command('status'))
async def status_command(message: Message, state: FSMContext):
    """Обработка команды /status - показывает статус текущих задач"""
    
    await state.clear()
    await process_show_status(message)


@dp.callback_query(F.data == 'btn_status')
async def inline_status_command(query: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки 'Статус задач'"""
    
    await query.answer()
    await state.clear()
    await process_show_status(query.message)
    

async def process_show_status(message: Message):
    """Получаем статус задач пользователя"""
    
    # Получаем все задачи пользователя
    tasks = await db_manage.get_parsing_tasks_by_user(message.from_user.id)
    
    if not tasks:
        await message.edit_text(
            '📊 <b>Статус задач</b>\n\n'
            'У вас нет активных задач парсинга.\n'
            'Создайте новую задачу кнопкой "Парсинг"',
            reply_markup=user_main_menu()
        )
        return
    
    # Формируем сообщение со статусами
    response = "📊 <b>Ваши задачи парсинга:</b>\n\n"
    
    for task in tasks[-5:]:  # Показываем последние 5 задач
        status_emoji = {
            ParsingTaskStatus.NEW: "🆕",
            ParsingTaskStatus.PROCESSING: "🔄",
            ParsingTaskStatus.COMPLETED: "✅",
            ParsingTaskStatus.ERROR: "❌"
        }.get(task.status, "❓")
        
        created_time = task.created_at.strftime("%d.%m.%Y %H:%M") if task.created_at else "N/A"
        
        response += (
            f"{status_emoji} <b>Задача #{task.id}</b>\n"
            f"Ссылка: {task.target_url[:50]}...\n"
            f"Статус: {task.status.value}\n"
            f"Создана: {created_time}\n"
            f"{'-' * 30}\n"
        )
    
    if len(tasks) > 5:
        response += f"\n... и еще {len(tasks) - 5} задач. Показаны последние 5."
    
    try:
        await message.edit_text(
            text=response,
            reply_markup=user_main_menu(),
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
    except TelegramBadRequest:
        await message.answer(
            text=response,
            reply_markup=user_main_menu(),
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )