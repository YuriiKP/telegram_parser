import asyncio

from aiogram import filters 
from aiogram.types import Message

from loader import dp, bot
from handlers import dp, bot
from loader import db_manage



async def main():
    await db_manage.create_tables()
    
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main()) 