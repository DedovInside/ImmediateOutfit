"""
FSM-состояния для диалога бота.
"""
from aiogram.fsm.state import State, StatesGroup


class OutfitForm(StatesGroup):
    """Состояния пошагового опроса."""
    gender = State()         # Вопрос 0: Пол
    occasion = State()       # Вопрос 1: Куда идёшь?
    activity = State()       # Вопрос 2: Насколько насыщенный день?
    priority = State()       # Вопрос 3: Что важнее сегодня?
    style = State()          # Вопрос 4: Стиль
    result = State()         # Показ результатов
    check_outfit = State()   # «Проверить мой образ» - ожидание текста

