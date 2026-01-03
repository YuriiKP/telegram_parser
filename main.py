import asyncio

from aiogram import filters 
from aiogram.types import Message

from loader import dp, bot
from handlers import dp, bot
from loader import db_manage
from middlewares import SubscriptionMiddleware
from subscription_checker import start_subscription_checker



async def main():
    await db_manage.create_tables()
    
    # Регистрируем middleware для проверки подписки
    dp.message.outer_middleware(SubscriptionMiddleware(db_manage))
    dp.callback_query.outer_middleware(SubscriptionMiddleware(db_manage))
    
    # Запускаем фоновую проверку подписок в отдельной задаче
    asyncio.create_task(start_subscription_checker())
    
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main()) 