from aiogram.filters.callback_data import CallbackData



class CB_ModerAdmins(CallbackData, prefix='moder_admins'):
    action: str
    status_user: str