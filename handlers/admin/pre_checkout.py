
from aiogram.types import LabeledPrice, PreCheckoutQuery, Message

from loader import dp



@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)