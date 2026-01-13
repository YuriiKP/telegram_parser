import asyncio
import logging
import os
import json
from datetime import datetime

from aiogram.types import BufferedInputFile, LinkPreviewOptions
from telethon.errors import FloodWaitError

from loader import db_manage, bot
from parser.telegram_parser import TelegramParser
from storage import ParsingTask, ParsingTaskStatus, SystemAccountStatus, ParsingType



logger = logging.getLogger(__name__)


async def process_task(task: ParsingTask):
    """Обработать одну задачу парсинга с retry при ошибках аккаунта"""
    MAX_RETRIES = 2  # Максимум 2 попытки (включая первую)
    attempt = 0
    last_error = None
    
    while attempt < MAX_RETRIES:
        attempt += 1
        account = await db_manage.get_free_account()
        if not account:
            logger.warning(f"Нет свободных аккаунтов для задачи {task.id}")
            # Если это повторная попытка и нет аккаунтов, выходим
            if attempt > 1:
                logger.error(f"Задача {task.id} не может быть выполнена: нет свободных аккаунтов после {attempt-1} ошибок")
            return

        try:
            # Обновляем статус задачи как processing
            await db_manage.update_parsing_task_status(task.id, ParsingTaskStatus.PROCESSING)
            
            logger.info(f"Попытка {attempt}/{MAX_RETRIES} обработки задачи {task.id} с аккаунтом {account.session}")

            # Получаем настройки пользователя
            user = await db_manage.get_user_by_id(task.creator_id)
            parse_only_active = user.parse_only_active
            collect_bio = user.collect_bio

            # Инициализируем парсер с передачей db_manager для обновления статуса ошибок и task_id для проверки отмены
            async with TelegramParser(
                session_path=account.session,
                config_path=account.json,
                db_manager=db_manage,
                task_id=task.id,
                parse_only_active=parse_only_active,
                collect_bio=collect_bio
            ) as parser:
                
                # Выбираем метод парсинга в зависимости от типа
                if task.parsing_type == ParsingType.CHAT_MEMBERS:
                    users_data = await parser.parse_users_chat(task.target_url)
                elif task.parsing_type == ParsingType.CHAT_WRITERS:
                    users_data = await parser.parse_users_from_history(task.target_url)
                elif task.parsing_type == ParsingType.CHANNEL_COMMENTERS:
                    users_data = await parser.parse_channel_commenters(task.target_url)
                elif task.parsing_type == ParsingType.CHANNEL_SUBSCRIBERS:
                    users_data = await parser.parse_channel_subscribers(task.target_url)
                else:
                    # fallback на парсинг участников чата
                    users_data = await parser.parse_users_chat(task.target_url)

                
                # Отправляем файлы пользователю
                if users_data:
                    try:
                        # Создаем TXT и Excel файл
                        txt_bytes_io = parser.get_txt_bytes(users_data)
                        excel_bytes_io = parser.get_excel_bytes(users_data)
                        
                        # Текстовое описание типа парсинга
                        type_description = {
                            ParsingType.CHAT_MEMBERS: "участников чата",
                            ParsingType.CHAT_WRITERS: "писавших в чат",
                            ParsingType.CHANNEL_COMMENTERS: "комментаторов канала",
                            ParsingType.CHANNEL_SUBSCRIBERS: "подписчиков канала"
                        }.get(task.parsing_type, "участников")
                        
                        # Отправляем сообщение пользователю
                        await bot.send_message(
                            chat_id=task.creator_id,
                            text=f"✅ Задача парсинга #{task.id} завершена!\n"
                                 f"Тип парсинга: {type_description}\n"
                                 f"Ссылка: {task.target_url}\n"
                                 f"Найдено участников: {len(users_data)}\n\n"
                                 f"Файлы с результатами:",
                            link_preview_options=LinkPreviewOptions(is_disabled=True)
                        )
                        
                        # Отправляем TXT файл (преобразуем BytesIO в bytes)
                        if txt_bytes_io:
                            await bot.send_document(
                                chat_id=task.creator_id,
                                document=BufferedInputFile(file=txt_bytes_io.getvalue(), filename="users.txt"),
                                caption=f"TXT файл с данными участников (задача #{task.id})"
                            )
                        
                        # Отправляем Excel файл (преобразуем BytesIO в bytes)
                        if excel_bytes_io:
                            await bot.send_document(
                                chat_id=task.creator_id,
                                document=BufferedInputFile(file=excel_bytes_io.getvalue(), filename="users.xlsx"),
                                caption=f"Excel файл с данными участников (задача #{task.id})"
                            )
                        
                        logger.info(f"Файлы отправлены пользователю {task.creator_id} для задачи {task.id}")
                        
                    except Exception as e:
                        logger.error(f"Ошибка при отправке файлов для задачи {task.id}: {e}")
                        # Отправляем сообщение об ошибке
                        await bot.send_message(
                            chat_id=task.creator_id,
                            text=f"❌ Задача #{task.id} завершена с ошибкой при отправке файлов"
                        )
                else:
                    await bot.send_message(
                        chat_id=task.creator_id,
                        text=f"⚠️ Задача #{task.id} завершена, но данные не найдены.\n"
                             f"Ссылка: {task.target_url}"
                    )

                # Обновляем статус задачи как completed
                await db_manage.update_parsing_task_status(task.id, ParsingTaskStatus.COMPLETED)
                logger.info(f"Задача {task.id} завершена успешно. Кол-во собранных юзеров: {len(users_data)}")
                
                # Успешное выполнение - выходим из цикла retry
                return

        except asyncio.CancelledError:
            logger.info(f"Задача {task.id} была отменена пользователем")
            # Статус уже CANCELLED, ничего не делаем
            # Отправляем уведомление пользователю
            await bot.send_message(
                chat_id=task.creator_id,
                text=f"🛑 Задача парсинга #{task.id} была отменена."
            )
            # При отмене не пытаемся повторять
            return
            
        except FloodWaitError as e:
            logger.error(f"FloodWait ошибка для аккаунта {account.session}: {e}")
            last_error = e
            # FloodWait - ошибка аккаунта, пробуем другой аккаунт
            logger.info(f"Пробуем другой аккаунт для задачи {task.id} из-за FloodWait")
            continue
            
        except Exception as e:
            logger.error(f"Ошибка при обработке задачи {task.id} (попытка {attempt}): {e}")
            last_error = e
            
            # Проверяем, является ли ошибка связанной с аккаунтом
            error_str = str(e).lower()
            is_account_error = any(keyword in error_str for keyword in [
                'auth', 'authorization', 'phone', 'sign in', 'login',
                'session', 'not authorized', 'banned', 'flood'
            ])
            
            if is_account_error and attempt < MAX_RETRIES:
                logger.info(f"Ошибка аккаунта, пробуем другой аккаунт для задачи {task.id}")
                continue
            else:
                # Не аккаунтная ошибка или достигнут лимит попыток
                break
                
        finally:
            # Освобождаем аккаунт (устанавливаем статус OK, если он не в состоянии ошибки)
            # Проверяем текущий статус аккаунта
            if account:
                current_account = await db_manage.get_system_account_by_session(account.session)
                if current_account and current_account.status == SystemAccountStatus.IS_BUSY:
                    # Если аккаунт все еще занят (не был помечен как ошибка), освобождаем его
                    await db_manage.set_system_account_status(account.session, SystemAccountStatus.OK)

    # Если дошли сюда, значит все попытки исчерпаны или произошла неаккаунтная ошибка
    logger.error(f"Задача {task.id} не выполнена после {attempt} попыток. Последняя ошибка: {last_error}")
    # Обновляем статус как error
    await db_manage.update_parsing_task_status(task.id, ParsingTaskStatus.ERROR)
    
    # Отправляем сообщение об ошибке пользователю
    await bot.send_message(
        chat_id=task.creator_id,
        text=f"❌ Задача парсинга #{task.id} завершена с ошибкой после {attempt} попыток"
    )


async def worker():
    """Основной цикл воркера"""
    logger.info("Воркер запущен. Начинаем мониторинг задач...")

    while True:
        try:
            # Получаем новые задачи
            tasks = await db_manage.get_new_parsing_tasks()

            if tasks:
                logger.info(f"Найдено {len(tasks)} новых задач")
                # Обрабатываем каждую задачу последовательно
                for task in tasks:
                    await process_task(task)
                # tasks_coroutines = [process_task(task) for task in tasks]
                # await asyncio.gather(*tasks_coroutines)
            else:
                logger.debug("Новых задач нет")

        except Exception as e:
            logger.error(f"Ошибка в основном цикле воркера: {e}")

        # Ждем 10 секунд
        await asyncio.sleep(10)
