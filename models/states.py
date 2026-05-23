"""
FSM-состояния для диалога бота.
"""
from aiogram.fsm.state import State, StatesGroup


class OutfitForm(StatesGroup):
    """Состояния пошагового опроса."""
    gender = State()         # Вопрос 0: Пол
    occasion = State()       # Вопрос 1: Куда идёшь?
    weather = State()        # Вопрос 2: Какая погода?
    activity = State()       # Вопрос 3: Насколько насыщенный день?
    priority = State()       # Вопрос 4: Что важнее сегодня?
    mood = State()           # Вопрос 5: Вайб / настроение образа
    budget = State()         # Вопрос 6: Бюджет
    style = State()          # Вопрос 7: Стиль
    result = State()         # Показ результатов
    check_outfit = State()   # «Проверить мой образ» - ожидание текста
    item_anchor = State()    # Ожидание ключевой вещи пользователя
    weather_city = State()   # Ожидание названия города для авто-определения погоды
    profile_colors = State()     # Ввод любимых цветов
    profile_disliked = State()   # Ввод анти-предпочтений
    profile_key_items = State()  # Ввод ключевых вещей гардероба
    feedback_comment = State()   # Опциональный комментарий после низкой оценки
