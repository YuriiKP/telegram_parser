from aiogram.filters import Filter
from aiogram.types import Message 

from loader import db_manage


class IsMainAdmin(Filter):
    def __init__(self) -> None:
        pass

    async def __call__(self, message: Message) -> bool:
        status_user = await db_manage.get_status_user(message.from_user.id)
        
        return status_user == 'main_admin'



class IsAdmin(Filter):
    def __init__(self) -> None:
        pass

    async def __call__(self, message: Message) -> bool:
        status_user = await db_manage.get_status_user(message.from_user.id)
        
        return status_user == 'admin' or status_user == 'main_admin'



class IsUser(Filter):
    def __init__(self) -> None:
        pass

    async def __call__(self, message: Message) -> bool:
        status_user = await db_manage.get_status_user(message.from_user.id)
        
        return status_user == 'user' or status_user == 'admin' or status_user == 'main_admin'