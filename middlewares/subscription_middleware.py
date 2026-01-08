from datetime import datetime
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from storage import User, DB_M


class SubscriptionMiddleware(BaseMiddleware):
    """Middleware для проверки активной подписки пользователя"""
    
    def __init__(self, db_manage):
        self.db_manage: DB_M = db_manage
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем user_id из события
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        else:
            return await handler(event, data)
        
        # Исключаем команду /start и хендлеры оплаты
        if isinstance(event, Message) and event.text and event.text.startswith(('/start', '/help')):
            return await handler(event, data)
        
        # Исключаем callback_data связанные с оплатой
        if isinstance(event, CallbackQuery) and event.data:
            if event.data.startswith(('btn_buy', 'btn_main_menu', 'btn_help', 'btn_parse', 'btn_subscription')) or 'pay' in event.data.lower():
                return await handler(event, data)
        
        # Проверяем подписку в базе данных
        user = await self.db_manage.get_user_by_id(user_id)
        if user:
            if user.status_user in ('admin', 'main_admin'):
                return await handler(event, data)
            
            # Проверяем, не истекла ли подписка или подписки никогда не было
            elif user.subscription_end is None or user.subscription_end < datetime.now():
                # Подписка истекла
                if isinstance(event, Message):
                    await event.answer("У вас нет активной подписки")
                elif isinstance(event, CallbackQuery):
                    await event.answer("У вас нет активной подписки", show_alert=True)
                return  # Прерываем обработку
        
            # Если проверка пройдена, продолжаем обработку
            return await handler(event, data)
        else: 
            return