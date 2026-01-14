import re
import logging
import asyncio

from aiogram.types import Message, CallbackQuery, LinkPreviewOptions, ChatMemberAdministrator, ChatMemberOwner
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram import F
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.utils.keyboard import InlineKeyboardBuilder

from loader import dp, bot, db_manage
from keyboards import *
from storage import ParsingTaskStatus, ParsingType
from utils.states import State_Parsing



logger = logging.getLogger(__name__)


# Обработчики инлайн кнопок
@dp.callback_query(F.data == 'btn_parse')
async def parse_command(query: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки 'Парсинг'"""
    
    # Проверяем, есть ли у пользователя активные задачи (NEW или PROCESSING)
    active_tasks = await db_manage.get_active_parsing_tasks_by_user(query.message.chat.id)
    # Получаем пользователя для меню
    user = await db_manage.get_user_by_id(query.from_user.id)
    if active_tasks:
        # Формируем сообщение с информацией об активных задачах
        task_info = "\n".join(
            f"• Задача #{task.id}: {task.status.value} (создана {task.created_at.strftime('%d.%m.%Y %H:%M')})"
            for task in active_tasks[:2]  # Показываем до 3 задач
        )
        if len(active_tasks) > 3:
            task_info += f"\n• ... и ещё {len(active_tasks) - 3} задач"
        
        await query.message.edit_text(
            f"⏳ <b>У вас уже есть активная задача парсинга!</b>\n\n"
            f"Вы можете запустить только одну задачу одновременно.\n\n"
            f"<b>Активные задачи:</b>\n{task_info}\n\n"
            f"Статус задач можно проверить кнопкой <b>\"Статус задач\"</b>.",
            reply_markup=user_main_menu(user),
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
        return
    
    
    # Устанавливаем состояние ожидания типа парсинга
    await state.set_state(State_Parsing.waiting_for_parsing_type)
    
    # Получаем текущую настройку пользователя
    user = await db_manage.get_user_by_id(query.from_user.id)
    parse_only_active_text = "✅" if user.parse_only_active else "❌"
    collect_bio_text = "✅" if user.collect_bio else "❌"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="👥 Парсинг участников чата", callback_data='parsing_type_chat_members')
    builder.button(text="✍️ Парсинг писавших в чат", callback_data='parsing_type_chat_writers')
    builder.button(text="💬 Парсинг комментаторов канала", callback_data='parsing_type_channel_commenters')
    builder.button(text="📢 Парсинг подписчиков канала", callback_data='parsing_type_channel_subscribers')
    builder.button(text=f"Только активных: {parse_only_active_text}", callback_data='btn_only_active')
    builder.button(text=f"Сбор био: {collect_bio_text}", callback_data='btn_collect_bio')
    builder.button(text=btn_main_menu, callback_data='btn_main_menu')
    builder.adjust(1, 1, 1, 1, 2, 1)
    
    await query.message.edit_text(
        f"<b>Выберите тип парсинга:</b>\n\n"
        f"<b>Настройки:</b>\n"
        f"    • 🎯 Только активных: {parse_only_active_text}\n"
        f"    • 📝 Сбор био: {collect_bio_text}\n\n "
        "<i>— 'Только активных' - Собираются те, кто был в сети максимум 1-2 дня назад.\n"
        "— При активной настройке 'Сбор био' собираются описания профиля. "
        "Из-за ограничений Телеграм время парсинга увеличивается. 1000 пользователей - около 19 минут.</i>",
        reply_markup=builder.as_markup()
    )


@dp.callback_query(F.data == 'btn_only_active')
async def toggle_only_active_handler(query: CallbackQuery, state: FSMContext):
    """Обработка переключения настройки 'Только активных'"""
    # Получаем пользователя
    user = await db_manage.get_user_by_id(query.from_user.id)
    
    # Инвертируем текущее значение
    new_value = not user.parse_only_active
    await db_manage.update_user(query.from_user.id, parse_only_active=new_value)

    await parse_command(query, state)
    

@dp.callback_query(F.data == 'btn_collect_bio')
async def toggle_collect_bio_handler(query: CallbackQuery, state: FSMContext):
    """Обработка переключения настройки 'Сбор био'"""
    # Получаем пользователя
    user = await db_manage.get_user_by_id(query.from_user.id)
    
    # Инвертируем текущее значение
    new_value = not user.collect_bio
    await db_manage.update_user(query.from_user.id, collect_bio=new_value)

    await parse_command(query, state)
    
    

@dp.callback_query(F.data.startswith('parsing_type_'))
async def process_parsing_type_selection(query: CallbackQuery, state: FSMContext):
    """Обработка выбора типа парсинга"""
    parsing_type_map = {
        'parsing_type_chat_members': ParsingType.CHAT_MEMBERS,
        'parsing_type_chat_writers': ParsingType.CHAT_WRITERS,
        'parsing_type_channel_commenters': ParsingType.CHANNEL_COMMENTERS,
        'parsing_type_channel_subscribers': ParsingType.CHANNEL_SUBSCRIBERS,
    }
    
    parsing_type = parsing_type_map.get(query.data)
    if not parsing_type:
        await query.answer("Неизвестный тип парсинга")
        return
    
    # Сохраняем тип парсинга в состоянии
    await state.update_data(parsing_type=parsing_type)
    
    # Для парсинга подписчиков канала переходим в специальное состояние
    if parsing_type == ParsingType.CHANNEL_SUBSCRIBERS:
        await state.set_state(State_Parsing.waiting_for_channel)
        
        bot_info = await bot.get_me() # Получаем username бота
        url = f"t.me/{bot_info.username}?startchannel&admin=invite_users+promote_members"

        builder = InlineKeyboardBuilder()
        builder.button(text="➕ Добавить бота в админы канала", url=url)
        builder.button(text=btn_back, callback_data='btn_parse')
        builder.adjust(1)
        
        await query.message.edit_text(
            "📢 <b>Парсинг подписчиков канала</b>\n\n"
            "Для парсинга подписчиков канала боту <b>нужны права на добавление участников и администраторов.</b>\n\n"
            "1. Нажмите кнопку ниже, чтобы добавить бота в админы канала\n"
            "2. Перешлите любой пост с канала или отправьте ссылку на канал\n"
            "3. Начнется сбор подписчиков канала\n\n"
            "<i>Бот автоматически создаст одноразовую пригласительную ссылку, "
            "по которой вступит сервисный аккаунт и начнет парсинг подписчиков, после " \
            "завершения парсинга можно всех удалить.</i>",
            reply_markup=builder.as_markup()
        )
    else:
        # Для остальных типов переходим к ожиданию ссылки
        await state.set_state(State_Parsing.waiting_for_link)
        
        builder = InlineKeyboardBuilder()
        builder.button(text=btn_back, callback_data='btn_parse')
        
        await query.message.edit_text(
            "Отправьте ссылку на чат или канал в любом формате:",
            reply_markup=builder.as_markup()
        )


@dp.message(State_Parsing.waiting_for_channel)
async def process_channel_for_subscribers(message: Message, state: FSMContext):
    """Обработка поста или ссылки на канал для парсинга подписчиков"""
    # Получаем ссылку на канал из сообщения
    channel_link = None
    chat_id = None
    
    if message.forward_from_chat:
        # Если переслан пост с канала
        if message.forward_from_chat.type == 'channel':
            channel_link = f"https://t.me/{message.forward_from_chat.username}" if message.forward_from_chat.username else None
            if not channel_link:
                channel_link = f"t.me/c/{str(message.forward_from_chat.id)[4:]}"
            chat_id = message.forward_from_chat.id
    elif message.text:
        # Если отправлена ссылка
        channel_link = message.text.strip()
        # Пытаемся извлечь chat_id из ссылки (позже, при проверке прав)
    
    if not channel_link:
        await message.answer(
            "❌ Не удалось получить ссылку на канал.\n"
            "Пожалуйста, перешлите пост с канала или отправьте ссылку на канал."
        )
        return
    
    # Валидация ссылки
    telegram_pattern = r'^(https?://)?(t\.me/|telegram\.me/)?(@)?(\+?[a-zA-Z0-9_-]+)(/[0-9]+)?$'
    if not re.match(telegram_pattern, channel_link):
        await message.answer(
            "❌ Некорректная ссылка. Используйте ссылку на Telegram канал.\n"
            "Примеры:\n"
            "• https://t.me/channel_name\n"
            "• @channel_name\n"
            "• t.me/channel_name"
        )
        return
    
    # Проверяем права бота в канале
    try:
        # Получаем информацию о боте
        bot_info = await bot.get_me()
        
        # Если chat_id не получен из пересланного сообщения, пытаемся получить его из ссылки
        if not chat_id:
            # Пытаемся получить chat_id через получение информации о чате
            try:
                chat = await bot.get_chat(channel_link)
                chat_id = chat.id
            except Exception as e:
                logger.error(f"Не удалось получить chat_id для {channel_link}: {e}")
                await message.answer(
                    "❌ Не удалось получить информацию о канале.\n"
                    f"Убедитесь, что бот @{bot_info.username} имеет доступ к каналу и является администратором."
                )
                return
        
        # Получаем информацию о боте в конкретном чате
        bot_member = await bot.get_chat_member(chat_id=chat_id, user_id=bot_info.id)
        
        # Проверяем, является ли бот администратором или владельцем
        is_admin = isinstance(bot_member, ChatMemberAdministrator)
        can_promote_members = False
        can_invite_users = False
        
        if isinstance(bot_member, ChatMemberAdministrator):
            can_promote_members = bot_member.can_promote_members
            can_invite_users = bot_member.can_invite_users

        if not is_admin:
            raise TelegramForbiddenError
        
        if not can_promote_members or not can_invite_users:
            await message.answer(
                "❌ <b>У бота недостаточно прав в канале!</b>\n\n"
                f"Текущие права бота:\n"
                f"• Добавление администраторов: {'✅' if can_promote_members else '❌'}\n"
                f"• Приглашение пользователей: {'✅' if can_invite_users else '❌'}\n\n"
                "Для парсинга подписчиков канала боту нужны оба этих права.\n"
                "Пожалуйста, обновите права бота в настройках канала и попробуйте снова.",
                reply_markup=InlineKeyboardBuilder()
                    .button(
                        text="➕ Обновить права бота",
                        url=f"t.me/{bot_info.username}?startchannel&admin=invite_users+promote_members")
                    .as_markup()
            )
            return
        
        # Все проверки пройдены, создаем задачу парсинга
        task_id = await db_manage.create_parsing_task(
            creator_id=message.from_user.id,
            target_url=chat_id,
            parsing_type=ParsingType.CHANNEL_SUBSCRIBERS
        )
        
        # Очищаем состояние
        await state.clear()
        
        await message.answer(
            f"✅ <b>Задача парсинга подписчиков канала создана!</b>\n\n"
            f"<b>ID задачи:</b> {task_id}\n"
            f"<b>Канал:</b> {channel_link}\n\n"
            f"Бот автоматически создаст одноразовую пригласительную ссылку, "
            f"сервисный аккаунт вступит в канал и начнет парсинг подписчиков.\n\n"
            f"Статус можно проверить кнопкой <b>\"Статус задач\"</b> или командой /status\n"
            f"Ожидайте уведомления о завершения.",
            reply_markup=user_parsing_started(),
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
        
    except TelegramForbiddenError:
        await message.answer(
            "❌ <b>Бот не является администратором канала!</b>\n\n"
            "Пожалуйста, добавьте бота в администраторы канала с правами:\n"
            "• Добавление администраторов (promote members)\n"
            "• Приглашение пользователей (invite users)\n\n"
            "После добавления попробуйте снова отправить пост или ссылку на канал.",
            reply_markup=InlineKeyboardBuilder()
                .button(
                    text="➕ Добавить бота в админы канала",
                    url=f"t.me/{bot_info.username}?startchannel&admin=invite_users+promote_members")
                .as_markup()
        )
    
    except Exception as e:
        # Очищаем состояние
        await state.clear()

        logger.error(f"Ошибка при проверке прав бота или создании задачи: {str(e)}")
        user = await db_manage.get_user_by_id(message.from_user.id)
        await message.answer(
            f"❌ Ошибка при создании задачи:\n"
            f"Попробуйте позже или обратитесь в поддержку.\n\n",
            reply_markup=user_main_menu(user)
        )


@dp.message(State_Parsing.waiting_for_link)
async def process_parsing_link(message: Message, state: FSMContext):
    """Обработка ссылки на парсинг, отправленной пользователем"""
    link = message.text.strip()
    
    # Получаем сохраненный тип парсинга из состояния
    data = await state.get_data()
    parsing_type = data['parsing_type']
    
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
    telegram_pattern = r'^(https?://)?(t\.me/|telegram\.me/)?(@)?(\+?[a-zA-Z0-9_-]+)(/[0-9]+)?$'
    if not re.match(telegram_pattern, link):
        await message.answer(
            "❌ Некорректная ссылка. Используйте ссылку на Telegram чат/канал.\n"
            "Примеры:\n"
            "• https://t.me/chat_name\n"
            "• @chat_name\n"
            "• t.me/chat_name"
        )
        return
    
    # Создаем задачу парсинга с указанным типом
    try:
        task_id = await db_manage.create_parsing_task(
            creator_id=message.from_user.id,
            target_url=link,
            parsing_type=parsing_type
        )
        
        # Текстовое описание типа парсинга
        type_description = {
            ParsingType.CHAT_MEMBERS: "участников чата",
            ParsingType.CHAT_WRITERS: "писавших в чат",
            ParsingType.CHANNEL_COMMENTERS: "комментаторов канала",
            ParsingType.CHANNEL_SUBSCRIBERS: "подписчиков канала"
        }.get(parsing_type, "участников")
        
        await message.answer(
            f"✅ <b>Задача парсинга создана!</b>\n\n"
            f"<b>ID задачи:</b> {task_id}\n"
            f"<b>Тип парсинга:</b> {type_description}\n"
            f"<b>Ссылка:</b> {link}\n\n"
            f"Статус можно проверить кнопкой <b>\"Статус задач\"</b> или командой /status\n"
            f"Ожидайте уведомления о завершения.",
            reply_markup=user_parsing_started(),
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
        
    except Exception as e:
        user = await db_manage.get_user_by_id(message.from_user.id)
        await message.answer(
            f"❌ Ошибка при создании задачи:\n"
            f"Попробуйте позже или обратитесь в поддержку.",
            reply_markup=user_main_menu(user)
        )
        logger.error(f"Ошибка при создании задачи: {str(e)}")


@dp.callback_query(F.data == 'btn_cancel_task')
async def inline_cancel_task_command(query: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки 'Отменить задачу'"""
    await query.answer()
    
    # Получаем активные задачи пользователя
    active_tasks = await db_manage.get_active_parsing_tasks_by_user(query.from_user.id)
    user = await db_manage.get_user_by_id(query.from_user.id)
    if not active_tasks:
        await query.message.edit_text(
            "📭 <b>Нет активных задач для отмены.</b>\n\n"
            "У вас нет запущенных задач парсинга (NEW или PROCESSING).",
            reply_markup=user_main_menu(user)
        )
        return
    
    # Отменяем все активные задачи
    cancelled_count = 0
    errors = []
    for task in active_tasks:
        success, msg = await db_manage.cancel_parsing_task(task.id, user_id=query.from_user.id)
        if success:
            cancelled_count += 1
        else:
            errors.append(f"Задача #{task.id}: {msg}")
    
    # Формируем ответ
    if cancelled_count == 0:
        response = (
            "❌ <b>Не удалось отменить задачи:</b>\n"
            + "\n".join(errors)
        )
    else:
        response = (
            f"✅ <b>Отменено задач:</b> {cancelled_count}\n"
            f"• Все активные задачи переведены в статус CANCELLED.\n\n"
        )
        if errors:
            response += "<b>Ошибки при отмене:</b>\n" + "\n".join(errors) + "\n\n"
        response += "Теперь вы можете запустить новую задачу парсинга."
    
    await query.message.edit_text(
        response,
        reply_markup=user_main_menu(user)
    )


# ==================== Получение статуса задачи ====================
@dp.message(Command('status'))
async def status_command(message: Message, state: FSMContext):
    """Обработка команды /status - показывает статус текущих задач"""
    
    await state.clear()
    await process_show_status(message)


@dp.callback_query(F.data == 'btn_status')
async def inline_status_command(query: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки 'Статус задач'"""
    
    # await query.answer()
    await state.clear()
    await process_show_status(query.message)
    

async def process_show_status(message: Message):
    """Получаем статус задач пользователя"""    
    status_emoji_map = {
        ParsingTaskStatus.NEW: "🆕",
        ParsingTaskStatus.PROCESSING: "🔄",
        ParsingTaskStatus.COMPLETED: "✅",
        ParsingTaskStatus.ERROR: "❌",
        ParsingTaskStatus.CANCELLED: "🚫"
    }
    
    # Проверяем наличие активных задач
    has_active_tasks = False
    tasks = await db_manage.get_active_parsing_tasks_by_user(message.chat.id)
    if tasks:
        has_active_tasks = True
        text = "🔎 <b>Задачи в работе:</b>\n"
    else:
        tasks = await db_manage.get_parsing_tasks_by_user(message.chat.id)
        text = "📊 <b>Последние 5 задач парсинга:</b>\n\n"
        
        
    for task in tasks[:5]:  # Показываем последние 5 задач
        status_emoji = status_emoji_map.get(task.status, "❓")
        
        created_time = task.created_at.strftime("%d.%m.%Y %H:%M") if task.created_at else "N/A"
        
        text += (
            f"{status_emoji} <b>Задача #{task.id}</b>\n"
            f"Ссылка: {task.target_url}\n"
            f"Статус: {task.status.value}\n"
            f"Создана: {created_time}\n"
            f"{'-' * 30}\n"
        )
    
    if len(tasks) > 5:
        text += f"\n... и еще {len(tasks) - 5} задач."
    

    # Можно перенести в клавиатуры
    ############################################################################
    # Создаем клавиатуру
    builder = InlineKeyboardBuilder()
    
    if has_active_tasks:
        builder.button(text=btn_cancel_task, callback_data='btn_cancel_task')
    
    builder.button(text="🔄 Обновить", callback_data='btn_status')
    builder.button(text="🏠 Главное меню", callback_data='btn_main_menu')
    builder.adjust(1)
    
    keyboard = builder.as_markup()
    ############################################################################


    try:
        await message.edit_text(
            text=text,
            reply_markup=keyboard,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
    except TelegramBadRequest:
        await message.answer(
            text=text,
            reply_markup=keyboard,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )