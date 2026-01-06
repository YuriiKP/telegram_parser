import os
import json
import io
import random
import asyncio
import logging
from typing import List, Dict, Optional, Union

import openpyxl
from openpyxl.styles import Font

from telethon import TelegramClient
from telethon.tl.types import Chat, User, Message, UserFull, PeerUser
from telethon.errors import FloodWaitError, UserAlreadyParticipantError
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.functions.channels import GetFullChannelRequest

from errors import JoinRequestSentError
from storage import SystemAccountStatus, ParsingTaskStatus, DB_M




class TelegramParser:
    """
    Класс для парсинга участников чатов и каналов Telegram.
    Использует библиотеку opentele для работы с Telegram API.
    """
    
    def __init__(
        self, 
        session_path: str, 
        config_path: str = None, 
        db_manager: DB_M = None, 
        account_session_path: str = None, 
        task_id: int = None
    ):
        """
        Инициализация клиента Telegram.
        
        Args:
            session_path (str): Путь к файлу сессии .session.
            config_path (str, optional): Путь к JSON файлу с api_id и api_hash. Defaults to None.
            db_manager: Менеджер БД для обновления статуса аккаунта при ошибках.
            account_session_path (str): Путь к сессии аккаунта в БД (для идентификации).
            task_id (int): ID задачи парсинга для проверки отмены.
        """
        self.session_path = session_path
        self.config_path = config_path
        self.db_manager = db_manager
        self.account_session_path = account_session_path or session_path
        self.task_id = task_id
        
        self.client = None
        self.logger = logging.getLogger(__name__)
        self.count = 0
        

    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.disconnect()
        if exc_type:
            print(f"Завершено с ошибкой: {exc_val}")


    async def connect(self):
        """
        Подключение к Telegram API.
        При ошибке авторизации (требуется номер телефона) помечает аккаунт как AUTH_REQUIRED.
        """
        try:
            api_id = 1
            api_hash = 'пусто'
            
            # Если config_path предоставлен, читаем конфигурацию из JSON файла
            if self.config_path:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                api_id = config.get('app_id')
                api_hash = config.get('app_hash')
                device_model = config.get('device_model', None) or config.get('device', None)
                system_version = config.get('system_version', None) or config.get('sdk', None)
                lang_code = config.get('lang_code', None)
                system_lang_code = config.get('system_lang_code', None) or config.get('system_lang_pack', None) or 'en-US'
                app_version = config.get('app_version', None)

                if not api_id or not api_hash:
                    raise ValueError("В JSON файле отсутствуют api_id или api_hash")
            

            self.client = TelegramClient(
                session=self.session_path,
                api_id=int(api_id) if api_id else None,
                api_hash=api_hash,

                device_model=device_model,
                system_version=system_version,
                lang_code=lang_code,
                system_lang_code=system_lang_code,
                app_version=app_version,

                connection_retries=3,
                timeout=9,
                raise_last_call_error=True
            )
            
            # Подключаемся без авторизации (не вызываем start())
            await self.client.connect()
            
            # Проверяем, авторизован ли пользователь
            if not await self.client.is_user_authorized():
                self.logger.error(f"Аккаунт не авторизован: {self.account_session_path}")
                if self.db_manager:
                    await self.db_manager.set_system_account_status(
                        self.account_session_path,
                        SystemAccountStatus.AUTH_REQUIRED
                    )
                raise Exception(f"Аккаунт не авторизован: {self.account_session_path}")
            
            self.logger.info("Успешное подключение к Telegram API")
        
        except FileNotFoundError:
            self.logger.error(f"Файл конфигурации не найден: {self.config_path}")
            raise
        
        except json.JSONDecodeError:
            self.logger.error(f"Ошибка чтения JSON файла: {self.config_path}")
            raise
        
        except FloodWaitError as e:
            self.logger.error(f"FloodWait ошибка для аккаунта {self.account_session_path}: {e}")
            if self.db_manager:
                await self.db_manager.set_system_account_status(
                    self.account_session_path,
                    SystemAccountStatus.FLOOD_WAIT
                )
            raise
        
        except Exception as e:
            self.logger.error(f"Ошибка подключения для аккаунта {self.account_session_path}: {e}")
            # Проверяем, является ли ошибка связанной с авторизацией
            error_str = str(e).lower()
            
            if any(keyword in error_str for keyword in ['phone', 'auth', 'sign in', 'login', 'session', 'not authorized']):
                if self.db_manager:
                    await self.db_manager.set_system_account_status(
                        self.account_session_path,
                        SystemAccountStatus.AUTH_REQUIRED
                    )
                raise
            else:
                if self.db_manager:
                    await self.db_manager.set_system_account_status(
                        self.account_session_path,
                        SystemAccountStatus.BANNED
                    )
                raise
    

    async def disconnect(self):
        """
        Отключение от Telegram API.
        """
        if self.client:
            await self.client.disconnect()
            self.logger.info("Отключение от Telegram API")

    
    async def check_cancelled(self):
        """Проверить, отменена ли задача (если task_id задан)"""
        if self.task_id is None or self.db_manager is None:
            return False
        
        self.count += 1
        if self.count % 10 == 0:
            task = await self.db_manager.get_parsing_task(self.task_id)
            if task and task.status == ParsingTaskStatus.CANCELLED:
                raise asyncio.CancelledError(f"Задача {self.task_id} отменена пользователем")

    async def _handle_account_error(self, error: Exception):
        """
        Обработать ошибку аккаунта и установить соответствующий статус в БД.
        
        Args:
            error: Исключение, которое произошло при работе с аккаунтом.
        """
        if not self.db_manager:
            return
        
        error_str = str(error).lower()
        
        # FloodWaitError
        if isinstance(error, FloodWaitError):
            await self.db_manager.set_system_account_status(
                self.account_session_path,
                SystemAccountStatus.FLOOD_WAIT
            )
            return
        
        # Ошибки авторизации
        if any(keyword in error_str for keyword in ['phone', 'auth', 'sign in', 'login', 'session', 'not authorized']):
            await self.db_manager.set_system_account_status(
                self.account_session_path,
                SystemAccountStatus.AUTH_REQUIRED
            )
            return
        
        # Другие ошибки, которые могут указывать на бан
        if any(keyword in error_str for keyword in ['banned', 'blocked', 'suspended', 'deleted']):
            await self.db_manager.set_system_account_status(
                self.account_session_path,
                SystemAccountStatus.BANNED
            )
            return
        
        # По умолчанию помечаем как BANNED (консервативный подход)
        await self.db_manager.set_system_account_status(
            self.account_session_path,
            SystemAccountStatus.BANNED
        )


    async def parse_users_chat(self, chat: str, limit: int = 10000) -> List[Dict]:
        """
        Парсинг участников чата (только если участники чата открыты).
        
        Args:
            chat (str): ссылка или id чата.
            limit (int): Максимальное количество участников для парсинга.
        
        Returns:
            List[Dict]: Список участников с их данными.
        """
        
       
        users_obj = []
        try:
################################################################################
            c = 0
################################################################################
            async for user in self.client.iter_participants(chat, limit=limit):
                if user.bot:
                    continue

                # Проверяем отмену
                await self.check_cancelled()

                users_obj.append(user)

################################################################################
                c += 1 
                if c == 5:
                    break
################################################################################    
        
            await asyncio.sleep(random.uniform(10, 20))

            users_data = []
            for user_obj in users_obj:
                # Проверяем отмену
                await self.check_cancelled()

                # Анти-флуд задержка ПЕРЕД тяжелым запросом
                await asyncio.sleep(random.uniform(0.1, 0.5))

                # Получаем полную информацию о пользователе, чтобы достать 'о себе'
                full_user = await self.client(GetFullUserRequest(user_obj))
                user_data = await self._extract_user_data(full_user)
                users_data.append(user_data)


        except asyncio.CancelledError:
            self.logger.info(f"Парсинг задачи {self.task_id} отменен")
            raise
        except ValueError as e:
            # Вступаем в чат, немного ждем и парсим
            self.logger.error(f"ValueError ошибка, пробую вступить в чат и повторить попытку: {e}")
            await self._join_chat(chat)
            await asyncio.sleep(10)
            return await self.parse_users_chat(chat)
        except FloodWaitError as e:
            self.logger.error(f"FloodWait ошибка: {e}, {e.seconds}")
            await self._handle_account_error(e)
            raise
        except Exception as e:
            self.logger.error(f"Ошибка парсинга участников из истории: {e}")
            await self._handle_account_error(e)
            raise
        
        return users_data
    

    async def parse_users_from_history(self, chat: str, limit: int = 10000) -> List[Dict]:
        """
        Парсинг участников из истории сообщений чата.
        
        Args:
            chat (str): ссылка или id чата.
            limit (int): Максимальное количество сообщений для анализа.
        
        Returns:
            List[Dict]: Список участников с их данными.
        """
        
        
        users_obj = []
        seen_users = set()
        try:
################################################################################
            c = 0
################################################################################
            async for comment in self.client.iter_messages(entity=chat, limit=limit):
                # Проверяем отмену каждые 10 сообщений
                await self.check_cancelled()
      
                if isinstance(comment.from_id, PeerUser) and comment.from_id.user_id not in seen_users:
                    seen_users.add(comment.from_id.user_id)
                    users_obj.append(comment.from_id) # Здесь добавляю объекты в список, чтобы можно было дальше получить информацию, просто по id это не получится
            
################################################################################
                c += 1 
                if c == 5:
                    break
################################################################################ 
            
            await asyncio.sleep(random.uniform(10, 20))

            users_data = []
            for user_obj in users_obj:
                # Проверяем отмену
                await self.check_cancelled()

                # Анти-флуд задержка ПЕРЕД тяжелым запросом
                await asyncio.sleep(random.uniform(0.1, 0.5))

                # Получаем полную информацию о пользователе, чтобы достать 'о себе'
                full_user = await self.client(GetFullUserRequest(user_obj))
                if full_user.users[0].bot:
                    continue

                user_data = await self._extract_user_data(full_user)
                users_data.append(user_data)

        
        except asyncio.CancelledError:
            self.logger.info(f"Парсинг задачи {self.task_id} отменен")
            raise
        except ValueError as e:
            # Вступаем в чат, немного ждем и парсим
            self.logger.error(f"ValueError ошибка, пробую вступить в чат и повторить попытку: {e}")
            await self._join_chat(chat)
            await asyncio.sleep(10)
            return await self.parse_users_from_history(chat)
        except FloodWaitError as e:
            self.logger.error(f"FloodWait ошибка: {e}, {e.seconds}")
            await self._handle_account_error(e)
            raise
        except Exception as e:
            self.logger.error(f"Ошибка парсинга участников из истории чата: {e}")
            await self._handle_account_error(e)
            raise
        
        return users_data
    

    async def parse_channel_commenters(self, chat: str, limit: int = 100) -> List[Dict]:
        """
        Парсинг комментаторов канала (если комментарии включены).
        
        Args:
            chat (str): ссылка на канал.
            limit (int): Максимальное количество комментариев для анализа.
        
        Returns:
            List[Dict]: Список комментаторов с их данными.
        """
        # Получаем полную информацию о канале
        try:
            full_channel = await self.client(GetFullChannelRequest(chat))
        except ValueError as e:
            # Вступаем в чат, немного ждем и парсим
            self.logger.error(f"ValueError ошибка, пробую вступить в чат и повторить попытку: {e}")
            # Если нужно ждать одобрения админом
            await self._join_chat(chat)            
            await asyncio.sleep(10)
        
        except Exception as e:
            self.logger.error(f"Ошибка получения информации о канале: {e}")
            await self._handle_account_error(e)
            raise
        
        # id привязанного чата
        chat = full_channel.full_chat.linked_chat_id
        if chat is None:
            return []
        return await self.parse_users_from_history(chat, limit)
    

    async def _extract_user_data(self, full_user_result) -> dict:
        """
        Извлечение данных пользователя из результата GetFullUserRequest.
        
        """
        # Базовый объект пользователя (имя, юзернейм, телефон)
        user_obj = full_user_result.users[0]
        
        # Объект расширенной информации (about)
        full_info = full_user_result.full_user

        user_data = {
            "id": user_obj.id,
            "username": user_obj.username or "",
            "first_name": user_obj.first_name or "",
            "last_name": user_obj.last_name or "",
            "phone": user_obj.phone or "",
            "premium": str(user_obj.premium),
            # "lang_code": user_obj.lang_code or "",
            "bio": full_info.about or ""
        }
        return user_data
    

    async def _join_chat(self, link: str) -> None:
        """
        Вступление в приватный чат по пригласительной ссылке

        Args:
            link str: Пригласительная ссылка
        
        """
        # Извлекаем хэш из ссылки
        invite_hash = link.split('/')[-1].replace('+', '')

        try:
            await self.client(ImportChatInviteRequest(invite_hash))
            print(f"Успешно вступили в чат по ссылке: {link}")
        
        except UserAlreadyParticipantError:
            print("Вы уже состоите в этом чате.")
        except FloodWaitError as e:
            print(f"Слишком много попыток! Нужно подождать {e.seconds} секунд.")
            await self._handle_account_error(e)
            raise
        except Exception as e:
            # Если нужно ждать одобрения
            if "successfully requested to join" in str(e):
                self.logger.warning("Отправлена заявка на вступление.")
                raise JoinRequestSentError("Нужно ждать одобрения админом")
            
            self.logger.error(f"Критическая ошибка вступления: {e}")
            await self._handle_account_error(e)
            raise
    

    def get_excel_bytes(self, users_data: List[Dict]) -> io.BytesIO:
        """
        Получение данных участников в виде Excel файла в памяти.
        
        Args:
            users_data (List[Dict]): Список данных участников.
        
        Returns:
            io.BytesIO: Excel файл в памяти.
        """
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Users"
        
        # Заголовки
        headers = ["ID", "Username", "First Name", "Last Name", "Phone", "Premium" "Bio"]
        for col_num, header in enumerate(headers, 1):
            cell = sheet.cell(row=1, column=col_num, value=header)
            cell.font = Font(bold=True)
        
        # Данные
        for row_num, user in enumerate(users_data, 2):
            sheet.cell(row=row_num, column=1, value=user["id"])
            sheet.cell(row=row_num, column=2, value=f"@{user["username"]}" if user["username"] else "")
            sheet.cell(row=row_num, column=3, value=user["first_name"])
            sheet.cell(row=row_num, column=4, value=user["last_name"])
            sheet.cell(row=row_num, column=5, value=user["phone"])
            sheet.cell(row=row_num, column=6, value="Да" if user["premium"] == "True" else "")
            sheet.cell(row=row_num, column=7, value=user["bio"])
        
        # Сохраняем в BytesIO вместо файла на диске
        excel_bytes = io.BytesIO()
        workbook.save(excel_bytes)
        excel_bytes.seek(0)
        
        self.logger.info("Excel данные подготовлены в памяти")
        return excel_bytes
    

    def get_txt_bytes(self, users_data: List[Dict]) -> io.BytesIO:
        """
        Получение данных участников в виде .txt файла в памяти.
        
        Args:
            users_data (List[Dict]): Список данных участников.
        
        Returns:
            io.BytesIO: TXT файл в памяти.
        """
        txt_content = io.StringIO()
        for user in users_data:
            if user['username']:
                txt_content.write(f"@{user['username']}\n")
        
        # Конвертируем StringIO в BytesIO для отправки через Telegram
        txt_bytes = io.BytesIO(txt_content.getvalue().encode('utf-8'))
        txt_bytes.seek(0)
        
        self.logger.info("TXT данные подготовлены в памяти")
        return txt_bytes