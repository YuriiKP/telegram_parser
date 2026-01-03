from datetime import datetime
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from storage import User


class SubscriptionMiddleware(BaseMiddleware):
    """Middleware для проверки активной подписки пользователя"""
    
    def __init__(self, db_manage):
        self.db_manage = db_manage
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
        if isinstance(event, Message) and event.text and event.text.startswith('/start'):
            return await handler(event, data)
        
        # Исключаем callback_data связанные с оплатой
        if isinstance(event, CallbackQuery) and event.data:
            if event.data.startswith('btn_buy') or 'pay' in event.data.lower():
                return await handler(event, data)
        
        # Проверяем подписку в базе данных
        async with self.db_manage.async_session() as session:
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if user and user.subscription_end:
                # Проверяем, не истекла ли подписка
                if user.subscription_end < datetime.now():
                    # Подписка истекла
                    if isinstance(event, Message):
                        await event.answer("У вас нет активной подписки")
                    elif isinstance(event, CallbackQuery):
                        await event.answer("У вас нет активной подписки", show_alert=True)
                    return  # Прерываем обработку
            elif user and user.subscription_end is None:
                # Подписки никогда не было
                if isinstance(event, Message):
                    await event.answer("У вас нет активной подписки")
                elif isinstance(event, CallbackQuery):
                    await event.answer("У вас нет активной подписки", show_alert=True)
                return  # Прерываем обработку
        
        # Если проверка пройдена, продолжаем обработку
        return await handler(event, data)