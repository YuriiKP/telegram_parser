from aiogram import filters, F
from aiogram.types import Message
from aiogram.types import BufferedInputFile
from aiogram.fsm.context import FSMContext

from loader import dp, bot
from filters import IsMainAdmin



####ДЛЯ ОПРЕДЕЛЕНИЯ ID МЕДИАФАЙЛА НА СЕРВЕРЕ ТГ####
####################################################
@dp.message(filters.Command('det'), IsMainAdmin())
async def process_start_bot(message: Message, state: FSMContext):     
    if message.photo:
        print(message.photo[-1].file_id)
        await message.answer(
            text=f'file_id = {message.photo[-1].file_id}\n\n'
            )
    
    if message.video:
        if message.video.width == message.video.height:
            video = (await bot.download(file=message.video)).read()
            video_note = await message.answer_video_note(video_note=BufferedInputFile(file=video, filename='video_note'))
            text = f'vodeo file_id = {message.video.file_id}\n\nvideo_note file_id = {video_note.video_note.file_id}'

        else:
            text = f'vodeo file_id = {message.video.file_id}'
        
        await message.answer(
            text=text
            )
        
    if message.document:
        print(message.document.file_id) 
        await message.answer(
            text=f'file_id = {message.document.file_id}\n\n'
            )
####################################################