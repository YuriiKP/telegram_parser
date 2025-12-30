import os 
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from dotenv import load_dotenv, find_dotenv

from storage import DB_M 


logging.basicConfig(level=logging.INFO)

load_dotenv()

# Тг бот
TG_TOKEN = os.getenv('TG_TOKEN')
TG_ADMIN = os.getenv('TG_ADMIN')
SQLALCHEMY_DATABASE_URL_TG = os.getenv('SQLALCHEMY_DATABASE_URL_TG')


bot = Bot(TG_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Инициализация базы данных
db_manage = DB_M(SQLALCHEMY_DATABASE_URL_TG)


deep_links_admin_manage = {}

symbols = (
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n',
    'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '0', '1', 
    '2', '3', '4', '5', '6', '7', '8', '9'
)