from aiogram.fsm.state import State, StatesGroup



class State_Ban_Admin(StatesGroup):
    msg = State()


class State_Mailing(StatesGroup):
    msg = State()
    add_button = State()


class State_Parsing(StatesGroup):
    """Состояние для процесса парсинга"""
    waiting_for_link = State()