"""
Хендлеры пошагового опроса и сценария "подбери под мою вещь".
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.inline import (
    activity_keyboard,
    budget_keyboard,
    gender_keyboard,
    occasion_keyboard,
    priority_keyboard,
    style_keyboard,
    weather_keyboard,
)
from models.states import OutfitForm
from services import storage

router = Router()


async def _goto_occasion(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(OutfitForm.occasion)
    await callback.message.edit_text(  # type: ignore[union-attr]
        "📍 <b>Куда ты сегодня идёшь?</b>",
        reply_markup=occasion_keyboard(),
        parse_mode="HTML",
    )


async def _finalize_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    storage.record_event(callback.from_user.id, "quiz_completed")
    await state.set_state(OutfitForm.result)
    await callback.message.edit_text(  # type: ignore[union-attr]
        "Отлично, понял тебя 👌\n\n"
        "Собираю варианты под твой день, погоду и текущий запрос...",
        parse_mode="HTML",
    )
    await callback.answer()

    from handlers.results import show_results

    await show_results(callback.message, state, callback.from_user.id)  # type: ignore[arg-type]


@router.callback_query(F.data == "start_quiz")
async def start_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.update_data(flow_mode="standard", shown_ids=[])
    storage.record_event(callback.from_user.id, "quiz_started", {"mode": "standard"})
    profile = storage.get_profile(callback.from_user.id)
    if profile and profile.gender:
        await state.update_data(gender=profile.gender, budget=profile.budget, style=profile.style)
        await _goto_occasion(callback, state)
    else:
        await state.set_state(OutfitForm.gender)
        await callback.message.edit_text(  # type: ignore[union-attr]
            "👤 <b>Для кого подбираем образ?</b>",
            reply_markup=gender_keyboard(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == "quick_start")
async def quick_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    profile = storage.get_profile(callback.from_user.id)
    await state.update_data(flow_mode="quick", shown_ids=[])
    storage.record_event(callback.from_user.id, "quiz_started", {"mode": "quick"})
    if profile:
        await state.update_data(
            gender=profile.gender,
            budget=profile.budget or "medium",
            style=profile.style or (profile.preferred_styles[0] if profile.preferred_styles else None),
        )
    data = await state.get_data()
    if data.get("gender"):
        await _goto_occasion(callback, state)
    else:
        await state.set_state(OutfitForm.gender)
        await callback.message.edit_text(  # type: ignore[union-attr]
            "👤 <b>Для кого подбираем образ?</b>",
            reply_markup=gender_keyboard(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == "item_flow_start")
async def item_flow_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.update_data(flow_mode="item", shown_ids=[])
    storage.record_event(callback.from_user.id, "item_flow_started")
    await state.set_state(OutfitForm.item_anchor)
    await callback.message.answer(  # type: ignore[union-attr]
        "👚 <b>Напиши вещь, вокруг которой хочешь собрать образ.</b>\n\n"
        "Например: <i>белая рубашка, черные брюки, голубые джинсы, кроссовки</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(OutfitForm.item_anchor)
async def process_item_anchor(message: Message, state: FSMContext) -> None:
    await state.update_data(item_anchor=message.text or "")
    profile = storage.get_profile(message.from_user.id)
    if profile and profile.gender:
        await state.update_data(gender=profile.gender, budget=profile.budget, style=profile.style)
        await state.set_state(OutfitForm.occasion)
        await message.answer(
            "📍 <b>Окей, теперь под какую ситуацию собираем образ?</b>",
            reply_markup=occasion_keyboard(),
            parse_mode="HTML",
        )
    else:
        await state.set_state(OutfitForm.gender)
        await message.answer(
            "👤 <b>Для кого подбираем образ?</b>",
            reply_markup=gender_keyboard(),
            parse_mode="HTML",
        )


@router.callback_query(OutfitForm.gender, F.data.startswith("gender:"))
async def process_gender(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[1]  # type: ignore[union-attr]
    await state.update_data(gender=value)
    storage.upsert_profile(callback.from_user.id, gender=value)
    storage.record_event(callback.from_user.id, "question_answered", {"step": "gender", "value": value})
    await _goto_occasion(callback, state)
    await callback.answer()


@router.callback_query(OutfitForm.occasion, F.data.startswith("occasion:"))
async def process_occasion(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[1]  # type: ignore[union-attr]
    await state.update_data(occasion=value)
    storage.record_event(callback.from_user.id, "question_answered", {"step": "occasion", "value": value})
    await state.set_state(OutfitForm.weather)
    await callback.message.edit_text(  # type: ignore[union-attr]
        "🌦 <b>Какая погода или ощущение по погоде сегодня?</b>",
        reply_markup=weather_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(OutfitForm.weather, F.data.startswith("weather:"))
async def process_weather(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[1]  # type: ignore[union-attr]
    await state.update_data(weather=value)
    storage.record_event(callback.from_user.id, "question_answered", {"step": "weather", "value": value})
    storage.record_event(callback.from_user.id, "weather_selected", {"value": value})
    await state.set_state(OutfitForm.activity)
    await callback.message.edit_text(  # type: ignore[union-attr]
        "🗓 <b>Насколько насыщенный у тебя день?</b>",
        reply_markup=activity_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(OutfitForm.activity, F.data.startswith("activity:"))
async def process_activity(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[1]  # type: ignore[union-attr]
    await state.update_data(activity=value)
    storage.record_event(callback.from_user.id, "question_answered", {"step": "activity", "value": value})
    await state.set_state(OutfitForm.priority)
    await callback.message.edit_text(  # type: ignore[union-attr]
        "🎯 <b>Что для тебя важнее сегодня?</b>",
        reply_markup=priority_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(OutfitForm.priority, F.data.startswith("priority:"))
async def process_priority(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[1]  # type: ignore[union-attr]
    await state.update_data(priority=value)
    storage.record_event(callback.from_user.id, "question_answered", {"step": "priority", "value": value})
    data = await state.get_data()
    if data.get("flow_mode") == "quick" and data.get("budget") and data.get("style"):
        await _finalize_quiz(callback, state)
        return
    await state.set_state(OutfitForm.budget)
    await callback.message.edit_text(  # type: ignore[union-attr]
        "💰 <b>Какой ориентир по бюджету сегодня?</b>",
        reply_markup=budget_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(OutfitForm.budget, F.data.startswith("budget:"))
async def process_budget(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[1]  # type: ignore[union-attr]
    await state.update_data(budget=value)
    storage.upsert_profile(callback.from_user.id, budget=value)
    storage.record_event(callback.from_user.id, "question_answered", {"step": "budget", "value": value})
    data = await state.get_data()
    if data.get("flow_mode") == "quick" and data.get("style"):
        await _finalize_quiz(callback, state)
        return
    await state.set_state(OutfitForm.style)
    await callback.message.edit_text(  # type: ignore[union-attr]
        "🎨 <b>Твой стиль ближе к:</b>",
        reply_markup=style_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(OutfitForm.style, F.data.startswith("style:"))
async def process_style(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[1]  # type: ignore[union-attr]
    await state.update_data(style=value, shown_ids=[])
    storage.upsert_profile(callback.from_user.id, style=value, preferred_styles=[value])
    storage.record_event(callback.from_user.id, "question_answered", {"step": "style", "value": value})
    await _finalize_quiz(callback, state)
