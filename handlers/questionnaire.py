"""
Хендлеры пошагового опроса (Questionnaire FSM).
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from models.states import OutfitForm
from keyboards.inline import (
    gender_keyboard,
    occasion_keyboard,
    activity_keyboard,
    priority_keyboard,
    style_keyboard,
)

router = Router()


# Начало опроса
@router.callback_query(F.data == "start_quiz")
async def start_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(OutfitForm.gender)
    await callback.message.edit_text(  # type: ignore[union-attr]
        "👤 <b>Для кого подбираем образ?</b>",
        reply_markup=gender_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# Вопрос 0 (пол) --> Вопрос 1
@router.callback_query(OutfitForm.gender, F.data.startswith("gender:"))
async def process_gender(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[1]  # type: ignore[union-attr]
    await state.update_data(gender=value)
    await state.set_state(OutfitForm.occasion)
    await callback.message.edit_text(  # type: ignore[union-attr]
        "📍 <b>Куда ты сегодня идёшь?</b>",
        reply_markup=occasion_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# Вопрос 1 --> Вопрос 2
@router.callback_query(OutfitForm.occasion, F.data.startswith("occasion:"))
async def process_occasion(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[1]  # type: ignore[union-attr]
    await state.update_data(occasion=value)
    await state.set_state(OutfitForm.activity)
    await callback.message.edit_text(  # type: ignore[union-attr]
        "🗓 <b>Насколько насыщенный у тебя день?</b>",
        reply_markup=activity_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# Вопрос 2 --> Вопрос 3
@router.callback_query(OutfitForm.activity, F.data.startswith("activity:"))
async def process_activity(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[1]  # type: ignore[union-attr]
    await state.update_data(activity=value)
    await state.set_state(OutfitForm.priority)
    await callback.message.edit_text(  # type: ignore[union-attr]
        "🎯 <b>Что для тебя важнее сегодня?</b>",
        reply_markup=priority_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# Вопрос 3 --> Вопрос 4
@router.callback_query(OutfitForm.priority, F.data.startswith("priority:"))
async def process_priority(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[1]  # type: ignore[union-attr]
    await state.update_data(priority=value)
    await state.set_state(OutfitForm.style)
    await callback.message.edit_text(  # type: ignore[union-attr]
        "🎨 <b>Твой стиль ближе к:</b>",
        reply_markup=style_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# Вопрос 4 --> Результаты
@router.callback_query(OutfitForm.style, F.data.startswith("style:"))
async def process_style(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[1]  # type: ignore[union-attr]
    await state.update_data(style=value, shown_ids=[])
    await state.set_state(OutfitForm.result)

    await callback.message.edit_text(  # type: ignore[union-attr]
        "Отлично, понял тебя 👌\n\n"
        "Подбираю образ под твой день - "
        "чтобы выглядел уместно и чувствовал себя уверенно...",
        parse_mode="HTML",
    )
    await callback.answer()

    # Импортируем здесь, чтобы избежать циклических зависимостей
    from handlers.results import show_results
    await show_results(callback.message, state)  # type: ignore[arg-type]

