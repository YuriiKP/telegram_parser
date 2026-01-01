import os
import json
import io
import logging
from typing import List, Dict, Optional, Union

import openpyxl
from openpyxl.styles import Font

from telethon import TelegramClient
from telethon.tl.types import Chat, User, Message
from telethon.errors import FloodWaitError




class TelegramParser:
    """
    Класс для парсинга участников чатов и каналов Telegram.
    Использует библиотеку opentele для работы с Telegram API.
    """
    
    def __init__(self, session_path: str, config_path: str):
        """
        Инициализация клиента Telegram.
        
        Args:
            session_path (str): Путь к файлу сессии .session.
            config_path (str): Путь к JSON файлу с api_id и api_hash.
        """
        self.session_path = session_path
        self.config_path = config_path
        self.client = None
        self.logger = logging.getLogger(__name__)
        
    async def connect(self):
        """
        Подключение к Telegram API.
        """
        try:
            # Чтение конфигурации из JSON файла
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            api_id = config.get('api_id')
            api_hash = config.get('api_hash')
            
            if not api_id or not api_hash:
                raise ValueError("В JSON файле отсутствуют api_id или api_hash")
            
            self.client = TelegramClient(
                session=self.session_path,
                api_id=int(api_id),
                api_hash=api_hash
            )
            await self.client.start()
            self.logger.info("Успешное подключение к Telegram API")
        except FileNotFoundError:
            self.logger.error(f"Файл конфигурации не найден: {self.config_path}")
            raise
        except json.JSONDecodeError:
            self.logger.error(f"Ошибка чтения JSON файла: {self.config_path}")
            raise
        except Exception as e:
            self.logger.error(f"Ошибка подключения: {e}")
            raise
    
    async def disconnect(self):
        """
        Отключение от Telegram API.
        """
        if self.client:
            await self.client.disconnect()
            self.logger.info("Отключение от Telegram API")
    
    async def _get_chat(self, url: str) -> Optional[Chat]:
        """
        Получение объекта чата по URL.
        
        Args:
            url (str): URL чата или канала.
        
        Returns:
            Optional[Chat]: Объект чата или None в случае ошибки.
        """
        try:
            chat = await self.client.get_entity(url)
            return chat
        except FloodWaitError as e:
            self.logger.error(f"FloodWait ошибка: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Ошибка получения чата: {e}")
            return None
    
    async def parse_users_chat(self, url: str, limit: int = 10000) -> List[Dict]:
        """
        Парсинг участников чата (только если участники чата открыты).
        
        Args:
            url (str): URL чата.
            limit (int): Максимальное количество участников для парсинга.
        
        Returns:
            List[Dict]: Список участников с их данными.
        """
        chat = await self._get_chat(url)
        if not chat:
            return []
        
        users_data = []
        try:
            async for participant in self.client.iter_participants(chat, limit=limit):
                user_data = await self._extract_user_data(participant)
                users_data.append(user_data)
        except FloodWaitError as e:
            self.logger.error(f"FloodWait ошибка: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Ошибка парсинга участников чата: {e}")
            raise
        
        return users_data
    
    async def parse_users_from_history(self, url: str, limit: int = 10000) -> List[Dict]:
        """
        Парсинг участников из истории сообщений чата.
        
        Args:
            url (str): URL чата.
            limit (int): Максимальное количество сообщений для анализа.
        
        Returns:
            List[Dict]: Список участников с их данными.
        """
        chat = await self._get_chat(url)
        if not chat:
            return []
        
        users_data = []
        seen_users = set()
        try:
            async for message in self.client.iter_messages(chat, limit=limit):
                if message.from_id and isinstance(message.from_id, User):
                    user_id = message.from_id.id
                    if user_id not in seen_users:
                        seen_users.add(user_id)
                        user_data = await self._extract_user_data(message.from_id)
                        users_data.append(user_data)
        except FloodWaitError as e:
            self.logger.error(f"FloodWait ошибка: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Ошибка парсинга участников из истории: {e}")
            raise
        
        return users_data
    
    async def parse_channel_commenters(self, url: str, limit: int = 10000) -> List[Dict]:
        """
        Парсинг комментаторов канала (если комментарии включены).
        
        Args:
            url (str): URL канала.
            limit (int): Максимальное количество комментариев для анализа.
        
        Returns:
            List[Dict]: Список комментаторов с их данными.
        """
        chat = await self._get_chat(url)
        if not chat:
            return []
        
        users_data = []
        seen_users = set()
        try:
            async for message in self.client.iter_messages(chat, limit=limit):
                if message.is_reply and message.from_id and isinstance(message.from_id, User):
                    user_id = message.from_id.id
                    if user_id not in seen_users:
                        seen_users.add(user_id)
                        user_data = await self._extract_user_data(message.from_id)
                        users_data.append(user_data)
        except FloodWaitError as e:
            self.logger.error(f"FloodWait ошибка: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Ошибка парсинга комментаторов канала: {e}")
            raise
        
        return users_data
    
    async def _extract_user_data(self, user: User) -> Dict:
        """
        Извлечение данных пользователя.
        
        Args:
            user (User): Объект пользователя.
        
        Returns:
            Dict: Словарь с данными пользователя.
        """
        user_data = {
            "id": user.id,
            "username": user.username if user.username else "",
            "first_name": user.first_name if user.first_name else "",
            "last_name": user.last_name if user.last_name else "",
            "phone": user.phone if user.phone else ""
        }
        return user_data
    
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
        headers = ["ID", "Username", "First Name", "Last Name", "Phone"]
        for col_num, header in enumerate(headers, 1):
            cell = sheet.cell(row=1, column=col_num, value=header)
            cell.font = Font(bold=True)
        
        # Данные
        for row_num, user in enumerate(users_data, 2):
            sheet.cell(row=row_num, column=1, value=user["id"])
            sheet.cell(row=row_num, column=2, value=user["username"])
            sheet.cell(row=row_num, column=3, value=user["first_name"])
            sheet.cell(row=row_num, column=4, value=user["last_name"])
            sheet.cell(row=row_num, column=5, value=user["phone"])
        
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
            line = f"{user['id']}|{user['username']}|{user['first_name']}|{user['phone']}\n"
            txt_content.write(line)
        
        # Конвертируем StringIO в BytesIO для отправки через Telegram
        txt_bytes = io.BytesIO(txt_content.getvalue().encode('utf-8'))
        txt_bytes.seek(0)
        
        self.logger.info("TXT данные подготовлены в памяти")
        return txt_bytes