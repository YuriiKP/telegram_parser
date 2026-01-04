import asyncio
import logging
import os
import json
from datetime import datetime

from aiogram.types import BufferedInputFile

from loader import db_manage, bot
from parser.telegram_parser import TelegramParser
from storage import ParsingTask, ParsingTaskStatus



logger = logging.getLogger(__name__)


async def process_task(task: ParsingTask):
    """Обработать одну задачу парсинга"""
    account = await db_manage.get_free_account()
    if not account:
        logger.warning(f"Нет свободных аккаунтов для задачи {task.id}")
        return

    try:
        logger.info(f"Начинаем обработку задачи {task.id} с аккаунтом {account.session}")

        # Инициализируем парсер
        async with TelegramParser(account.session, account.json) as parser:
            # Парсим участников чата
            users_data = await parser.parse_users_chat(task.target_url)

            #######################################
            print(users_data)
            #######################################

            # Отправляем файлы пользователю
            if users_data:
                try:
                    # Создаем Excel файл
                    excel_bytes = parser.get_excel_bytes(users_data)
                    
                    # Создаем TXT файл
                    txt_bytes = parser.get_txt_bytes(users_data)
                    
                    # Отправляем сообщение пользователю
                    await bot.send_message(
                        chat_id=task.creator_id,
                        text=f"✅ Задача парсинга #{task.id} завершена!\n"
                             f"Ссылка: {task.target_url}\n"
                             f"Найдено участников: {len(users_data)}\n\n"
                             f"Файлы с результатами:"
                    )
                    
                    # Отправляем Excel файл
                    await bot.send_document(
                        chat_id=task.creator_id,
                        document=BufferedInputFile(file=excel_bytes, filename="users.xlsx"),
                        caption=f"Excel файл с данными участников (задача #{task.id})"
                    )
                    
                    # Отправляем TXT файл
                    await bot.send_document(
                        chat_id=task.creator_id,
                        document=BufferedInputFile(file=txt_bytes, filename="users.txt"),
                        caption=f"TXT файл с данными участников (задача #{task.id})"
                    )
                    
                    logger.info(f"Файлы отправлены пользователю {task.creator_id} для задачи {task.id}")
                    
                except Exception as e:
                    logger.error(f"Ошибка при отправке файлов для задачи {task.id}: {e}")
                    # Отправляем сообщение об ошибке
                    await bot.send_message(
                        chat_id=task.creator_id,
                        text=f"❌ Задача #{task.id} завершена с ошибкой при отправке файлов: {str(e)}"
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

    except Exception as e:
        logger.error(f"Ошибка при обработке задачи {task.id}: {e}")
        # Обновляем статус как error
        await db_manage.update_parsing_task_status(task.id, ParsingTaskStatus.ERROR)
        
        # Отправляем сообщение об ошибке пользователю
        try:
            await bot.send_message(
                chat_id=task.creator_id,
                text=f"❌ Задача парсинга #{task.id} завершена с ошибкой:\n{str(e)}"
            )
        except Exception as send_error:
            logger.error(f"Не удалось отправить сообщение об ошибке: {send_error}")
    finally:
        # Освобождаем аккаунт
        await db_manage.set_system_account_busy(account.session, False)


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
