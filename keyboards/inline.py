"""
Фабрики InlineKeyboardMarkup для основных сценариев бота.
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def start_keyboard(has_profile: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="👗 Подобрать образ", callback_data="start_quiz")],
    ]
    if has_profile:
        rows.append([InlineKeyboardButton(text="⚡ Быстрый подбор", callback_data="quick_start")])
    rows.extend(
        [
            [InlineKeyboardButton(text="👚 Подобрать под мою вещь", callback_data="item_flow_start")],
            [InlineKeyboardButton(text="🔍 Проверить мой образ", callback_data="check_outfit")],
            [InlineKeyboardButton(text="🧬 Мой профиль", callback_data="profile_view")],
            [InlineKeyboardButton(text="✨ Premium", callback_data="premium_info")],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


GENDER_OPTIONS = [
    ("👦 Парень", "male"),
    ("👧 Девушка", "female"),
]

OCCASION_OPTIONS = [
    ("📚 Учёба / работа", "study_work"),
    ("🏠 Обычный день", "casual_day"),
    ("☕ Встреча / прогулка", "hangout"),
    ("❤️ Свидание", "date"),
    ("🎉 Мероприятие", "event"),
]

WEATHER_OPTIONS = [
    ("☀️ Тепло", "warm"),
    ("🌤 Переменчиво", "mild"),
    ("🧥 Холодно", "cold"),
    ("🌧 Дождь", "rain"),
]

ACTIVITY_OPTIONS = [
    ("😌 Спокойный, одно место", "calm"),
    ("🚶 Буду много двигаться", "active"),
    ("🔄 Несколько разных дел", "mixed"),
]

PRIORITY_OPTIONS = [
    ("🧸 Комфорт", "comfort"),
    ("⚖️ Баланс", "balance"),
    ("✨ Хочу выглядеть эффектно", "impressive"),
]

MOOD_OPTIONS = [
    ("🌿 Спокойно", "neutral"),
    ("🧶 Уютно", "cozy"),
    ("✨ Заметнее", "bright"),
    ("🧥 Собранно", "smart"),
]

BUDGET_OPTIONS = [
    ("💸 Экономно", "low"),
    ("💳 Средний", "medium"),
    ("💎 Можно вложиться", "high"),
]

STYLE_OPTIONS = [
    ("🤍 База / минимализм", "base_minimal"),
    ("👕 Casual", "casual"),
    ("🏃 Спортивный", "sport"),
    ("👔 Более классический", "classic"),
]


def _choice_keyboard(
    options: list[tuple[str, str]], prefix: str, width: int = 2, back: bool = False
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for text, data in options:
        builder.button(text=text, callback_data=f"{prefix}:{data}")
    builder.adjust(width)
    if back:
        builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back"))
    builder.row(InlineKeyboardButton(text="✖️ Отменить", callback_data="cancel_flow"))
    return builder.as_markup()


def gender_keyboard(back: bool = False) -> InlineKeyboardMarkup:
    return _choice_keyboard(GENDER_OPTIONS, "gender", width=2, back=back)


def occasion_keyboard(back: bool = False) -> InlineKeyboardMarkup:
    return _choice_keyboard(OCCASION_OPTIONS, "occasion", width=2, back=back)


def weather_keyboard(back: bool = False, show_auto: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for text, data in WEATHER_OPTIONS:
        builder.button(text=text, callback_data=f"weather:{data}")
    builder.adjust(2)
    if show_auto:
        builder.row(InlineKeyboardButton(text="📍 По моему городу", callback_data="weather_auto"))
    if back:
        builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back"))
    builder.row(InlineKeyboardButton(text="✖️ Отменить", callback_data="cancel_flow"))
    return builder.as_markup()


def activity_keyboard(back: bool = False) -> InlineKeyboardMarkup:
    return _choice_keyboard(ACTIVITY_OPTIONS, "activity", width=2, back=back)


def priority_keyboard(back: bool = False) -> InlineKeyboardMarkup:
    return _choice_keyboard(PRIORITY_OPTIONS, "priority", width=2, back=back)


def mood_keyboard(back: bool = False) -> InlineKeyboardMarkup:
    return _choice_keyboard(MOOD_OPTIONS, "mood", width=2, back=back)


def budget_keyboard(back: bool = False) -> InlineKeyboardMarkup:
    return _choice_keyboard(BUDGET_OPTIONS, "budget", width=2, back=back)


def style_keyboard(back: bool = False) -> InlineKeyboardMarkup:
    return _choice_keyboard(STYLE_OPTIONS, "style", width=2, back=back)


def outfit_result_keyboard(outfit_id: str, show_links: bool = True) -> InlineKeyboardMarkup:
    second_row = [InlineKeyboardButton(text="🖼 Референс", callback_data=f"reference:{outfit_id}")]
    if show_links:
        second_row.append(InlineKeyboardButton(text="🛍 Где искать", callback_data=f"links:{outfit_id}"))
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👍 Сохранить", callback_data=f"save:{outfit_id}"),
                InlineKeyboardButton(text="🧠 Почему подходит", callback_data=f"explain:{outfit_id}"),
            ],
            second_row,
            [
                InlineKeyboardButton(text="🔄 Показать ещё", callback_data="show_more"),
            ],
        ]
    )


def result_feedback_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👍 Полезно", callback_data="result_feedback:5"),
                InlineKeyboardButton(text="🤔 Норм", callback_data="result_feedback:3"),
                InlineKeyboardButton(text="👎 Мимо", callback_data="result_feedback:1"),
            ]
        ]
    )


def review_feedback_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👍 Да, помогло", callback_data="review_feedback:5"),
                InlineKeyboardButton(text="👌 Частично", callback_data="review_feedback:3"),
                InlineKeyboardButton(text="👎 Нет", callback_data="review_feedback:1"),
            ]
        ]
    )


def feedback_skip_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Пропустить", callback_data="feedback_comment_skip")]
        ]
    )


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✖️ Отменить", callback_data="cancel_flow")]
        ]
    )


def final_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Подобрать заново", callback_data="start_quiz")],
            [InlineKeyboardButton(text="⚡ Быстрый подбор", callback_data="quick_start")],
            [InlineKeyboardButton(text="👚 Под мою вещь", callback_data="item_flow_start")],
            [InlineKeyboardButton(text="🔍 Проверить мой образ", callback_data="check_outfit")],
            [InlineKeyboardButton(text="📂 Мои сохранённые", callback_data="show_saved")],
            [InlineKeyboardButton(text="🧬 Мой профиль", callback_data="profile_view")],
            [InlineKeyboardButton(text="✨ Premium", callback_data="premium_info")],
        ]
    )


def profile_keyboard(has_profile: bool = False) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="🎨 Любимые цвета", callback_data="profile_colors")]]
    rows.append([InlineKeyboardButton(text="🚫 Не люблю носить", callback_data="profile_disliked")])
    rows.append([InlineKeyboardButton(text="👕 Мои ключевые вещи", callback_data="profile_key_items")])
    if has_profile:
        rows.append([InlineKeyboardButton(text="⚡ Быстрый подбор", callback_data="quick_start")])
    rows.append([InlineKeyboardButton(text="⬅️ В главное меню", callback_data="menu_home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def premium_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🙋 Хочу early access", callback_data="premium_interest")],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu_home")],
        ]
    )
