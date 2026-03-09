"""
Фабрики InlineKeyboardMarkup для каждого шага диалога.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


# -----------------
# Стартовая кнопка
# -----------------
def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👗 Подобрать образ", callback_data="start_quiz")],
        ]
    )


# -----------------------
# Вопрос 0 - Пол
# -----------------------
GENDER_OPTIONS = [
    ("👦 Парень", "male"),
    ("👧 Девушка", "female"),
]

def gender_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for text, data in GENDER_OPTIONS:
        builder.button(text=text, callback_data=f"gender:{data}")
    builder.adjust(2)
    return builder.as_markup()


# -----------------------
# Вопрос 1 - Куда идёшь?
# -----------------------
OCCASION_OPTIONS = [
    ("📚 Учёба / работа", "study_work"),
    ("🏠 Обычный день", "casual_day"),
    ("☕ Встреча / прогулка", "hangout"),
    ("❤️ Свидание", "date"),
    ("🎉 Мероприятие", "event"),
]

def occasion_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for text, data in OCCASION_OPTIONS:
        builder.button(text=text, callback_data=f"occasion:{data}")
    builder.adjust(2)  # по 2 кнопки в ряд
    return builder.as_markup()


# ---------------------------------------
# Вопрос 2 - Насколько насыщенный день?
# ---------------------------------------
ACTIVITY_OPTIONS = [
    ("😌 Спокойный, одно место", "calm"),
    ("🚶 Буду много двигаться", "active"),
    ("🔄 Несколько разных дел", "mixed"),
]

def activity_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for text, data in ACTIVITY_OPTIONS:
        builder.button(text=text, callback_data=f"activity:{data}")
    builder.adjust(1)
    return builder.as_markup()


# ----------------------------------------
# Вопрос 3 - Что важнее сегодня?
# ----------------------------------------
PRIORITY_OPTIONS = [
    ("🧸 Комфорт", "comfort"),
    ("⚖️ Баланс", "balance"),
    ("✨ Хочу выглядеть эффектно", "impressive"),
]

def priority_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for text, data in PRIORITY_OPTIONS:
        builder.button(text=text, callback_data=f"priority:{data}")
    builder.adjust(1)
    return builder.as_markup()


# -------------------
# Вопрос 4 - Стиль
# -------------------
STYLE_OPTIONS = [
    ("🤍 База / минимализм", "base_minimal"),
    ("👕 Casual", "casual"),
    ("🏃 Спортивный", "sport"),
    ("👔 Более классический", "classic"),
]

def style_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for text, data in STYLE_OPTIONS:
        builder.button(text=text, callback_data=f"style:{data}")
    builder.adjust(2)
    return builder.as_markup()


# ---------------------------
# Кнопки после показа образа
# ---------------------------
def outfit_result_keyboard(outfit_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👍 Подходит", callback_data=f"save:{outfit_id}"),
                InlineKeyboardButton(text="🔄 Показать ещё", callback_data="show_more"),
            ],
        ]
    )


def final_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Проверить мой образ", callback_data="check_outfit"),
            ],
            [
                InlineKeyboardButton(text="🔁 Подобрать заново", callback_data="start_quiz"),
            ],
            [
                InlineKeyboardButton(text="📂 Мои сохранённые", callback_data="show_saved"),
            ],
        ]
    )

