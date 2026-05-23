"""
Хендлеры пошагового опроса и сценария "подбери под мою вещь".
"""
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import settings
from keyboards.inline import (
    activity_keyboard,
    budget_keyboard,
    cancel_keyboard,
    final_keyboard,
    gender_keyboard,
    mood_keyboard,
    occasion_keyboard,
    priority_keyboard,
    style_keyboard,
    weather_keyboard,
)
from models.states import OutfitForm
from services import storage
from services.ai_assistant import ItemOutfitSuggestion, ai_suggest_outfits_for_item, is_ai_enabled
from services.weather import fetch_weather
from handlers.ui import clear_clicked_keyboard

router = Router()

STEP_VIEW = {
    "gender": ("👤 <b>Для кого подбираем образ?</b>", gender_keyboard),
    "occasion": ("📍 <b>Куда ты сегодня идёшь?</b>", occasion_keyboard),
    "weather": ("🌦 <b>Какая погода или ощущение по погоде сегодня?</b>", weather_keyboard),
    "activity": ("🗓 <b>Насколько насыщенный у тебя день?</b>", activity_keyboard),
    "priority": ("🎯 <b>Что для тебя важнее сегодня?</b>", priority_keyboard),
    "mood": ("🪄 <b>Какой вайб образа хочется сегодня?</b>", mood_keyboard),
    "budget": ("💰 <b>Какой ориентир по бюджету сегодня?</b>", budget_keyboard),
    "style": ("🎨 <b>Твой стиль ближе к:</b>", style_keyboard),
}
STATE_BY_STEP = {
    "gender": OutfitForm.gender,
    "occasion": OutfitForm.occasion,
    "weather": OutfitForm.weather,
    "activity": OutfitForm.activity,
    "priority": OutfitForm.priority,
    "mood": OutfitForm.mood,
    "budget": OutfitForm.budget,
    "style": OutfitForm.style,
}


async def _show_step(callback: CallbackQuery, state: FSMContext, step: str, advance_from: str | None) -> None:
    data = await state.get_data()
    history = list(data.get("history", []))
    if advance_from:
        history.append(advance_from)
    await state.update_data(history=history)
    await state.set_state(STATE_BY_STEP[step])
    text, kb_fn = STEP_VIEW[step]
    await callback.message.edit_text(  # type: ignore[union-attr]
        text,
        reply_markup=kb_fn(back=bool(history)),
        parse_mode="HTML",
    )


async def _goto_occasion(callback: CallbackQuery, state: FSMContext) -> None:
    await _show_step(callback, state, "occasion", advance_from=None)


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
    await state.update_data(flow_mode="standard", shown_ids=[], history=[])
    storage.record_event(callback.from_user.id, "quiz_started", {"mode": "standard"})
    profile = storage.get_profile(callback.from_user.id)
    if profile and profile.gender:
        await state.update_data(gender=profile.gender, budget=profile.budget, style=profile.style)
        await _goto_occasion(callback, state)
    else:
        await _show_step(callback, state, "gender", advance_from=None)
    await callback.answer()


@router.callback_query(F.data == "quick_start")
async def quick_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    profile = storage.get_profile(callback.from_user.id)
    await state.update_data(flow_mode="quick", shown_ids=[], history=[])
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
        await _show_step(callback, state, "gender", advance_from=None)
    await callback.answer()


@router.callback_query(F.data == "item_flow_start")
async def item_flow_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.update_data(flow_mode="item", shown_ids=[], history=[])
    storage.record_event(callback.from_user.id, "item_flow_started")
    await state.set_state(OutfitForm.item_anchor)
    await clear_clicked_keyboard(callback)
    await callback.message.answer(  # type: ignore[union-attr]
        "👚 <b>Напиши вещь, вокруг которой хочешь собрать образ.</b>\n\n"
        "Например: <i>белая рубашка, черные брюки, голубые джинсы, кроссовки</i>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(OutfitForm.item_anchor)
async def process_item_anchor(message: Message, state: FSMContext) -> None:
    raw_item_anchor = (message.text or "").strip()
    profile = storage.get_profile(message.from_user.id)

    suggestions = await ai_suggest_outfits_for_item(raw_item_anchor, profile) if is_ai_enabled() else None
    if suggestions:
        storage.record_event(
            message.from_user.id,
            "ai_item_outfits_generated",
            {"count": len(suggestions), "query": raw_item_anchor[:120]},
        )
        await _send_ai_item_suggestions(message, raw_item_anchor, suggestions)
        await state.clear()
        return

    storage.record_event(
        message.from_user.id,
        "ai_item_outfits_fallback",
        {"ai_enabled": is_ai_enabled(), "query": raw_item_anchor[:120]},
    )
    await state.update_data(item_anchor=raw_item_anchor, item_anchor_raw=raw_item_anchor)
    if is_ai_enabled():
        await message.answer(
            "AI сейчас не смог собрать варианты, поэтому продолжу через быстрые кнопки.",
            parse_mode="HTML",
        )
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


def _format_ai_suggestion(suggestion: ItemOutfitSuggestion, index: int) -> str:
    parts = [
        f"<b>Вариант {index} — {escape(suggestion.title)}</b>",
        "",
        "<b>Что надеть:</b>",
        "\n".join(f"  • {escape(item)}" for item in suggestion.items),
        "",
        "<b>Почему подойдёт:</b>",
        "\n".join(f"  • {escape(item)}" for item in suggestion.why_it_fits),
        "",
        "<b>Как усилить:</b>",
        "\n".join(f"  • {escape(item)}" for item in suggestion.styling_tips),
    ]
    if suggestion.colors:
        parts.extend(["", "<b>Палитра:</b>", "\n".join(f"  • {escape(item)}" for item in suggestion.colors)])
    if suggestion.avoid:
        parts.extend(["", "<b>Лучше избегать:</b>", "\n".join(f"  • {escape(item)}" for item in suggestion.avoid)])
    return "\n".join(parts)


async def _send_ai_item_suggestions(
    message: Message,
    query: str,
    suggestions: list[ItemOutfitSuggestion],
) -> None:
    await message.answer(
        f"Собрал варианты вокруг запроса:\n<i>{escape(query[:300])}</i>",
        parse_mode="HTML",
    )
    for index, suggestion in enumerate(suggestions, start=1):
        await message.answer(
            _format_ai_suggestion(suggestion, index),
            parse_mode="HTML",
        )
    await message.answer(
        "Если хочешь точнее, запусти «Под мою вещь» ещё раз и добавь ситуацию, погоду или желаемый вайб.",
        reply_markup=final_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(OutfitForm.gender, F.data.startswith("gender:"))
async def process_gender(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[1]  # type: ignore[union-attr]
    await state.update_data(gender=value)
    storage.upsert_profile(callback.from_user.id, gender=value)
    storage.record_event(callback.from_user.id, "question_answered", {"step": "gender", "value": value})
    await _show_step(callback, state, "occasion", advance_from="gender")
    await callback.answer()


@router.callback_query(OutfitForm.occasion, F.data.startswith("occasion:"))
async def process_occasion(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[1]  # type: ignore[union-attr]
    await state.update_data(occasion=value)
    storage.record_event(callback.from_user.id, "question_answered", {"step": "occasion", "value": value})
    await _show_step(callback, state, "weather", advance_from="occasion")
    await callback.answer()


@router.callback_query(OutfitForm.weather, F.data.startswith("weather:"))
async def process_weather(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[1]  # type: ignore[union-attr]
    await state.update_data(weather=value)
    storage.record_event(callback.from_user.id, "question_answered", {"step": "weather", "value": value})
    # Два события намеренно: question_answered кормит dropoff_by_step,
    # отдельный weather_selected — метрику weather_usage_rate в storage.get_metrics().
    storage.record_event(callback.from_user.id, "weather_selected", {"value": value})
    await _show_step(callback, state, "activity", advance_from="weather")
    await callback.answer()


@router.message(OutfitForm.weather)
async def process_weather_free_text(message: Message) -> None:
    await message.answer(
        "На этом шаге я жду кнопку с погодой 🙂\n\n"
        "Выбери один из вариантов ниже или нажми «📍 По моему городу», чтобы я снова попросил город.",
        reply_markup=weather_keyboard(back=False),
        parse_mode="HTML",
    )


@router.callback_query(OutfitForm.weather, F.data == "weather_auto")
async def process_weather_auto(callback: CallbackQuery, state: FSMContext) -> None:
    storage.record_event(callback.from_user.id, "weather_auto_attempted")
    if not settings.OWM_API_KEY:
        await callback.answer(
            "Авто-погода пока не подключена, выбери вручную 🙂",
            show_alert=True,
        )
        return
    await state.set_state(OutfitForm.weather_city)
    await callback.message.answer(  # type: ignore[union-attr]
        "📍 <b>Напиши город или индекс</b> (например: Москва, Санкт-Петербург, 123056).\n\n"
        "Если передумал — /skip и вернёмся к ручному выбору.",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(OutfitForm.weather_city, F.text == "/skip")
async def cancel_weather_auto(message: Message, state: FSMContext) -> None:
    await state.set_state(OutfitForm.weather)
    await message.answer(
        "Окей, выбери погоду вручную:",
        reply_markup=weather_keyboard(back=False),
        parse_mode="HTML",
    )


@router.message(OutfitForm.weather_city)
async def process_weather_city(message: Message, state: FSMContext) -> None:
    city = (message.text or "").strip()[:60]
    if not city:
        await message.answer("Кажется, ничего не пришло. Напиши город или /skip для ручного выбора.")
        return

    snapshot = await fetch_weather(city, settings.OWM_API_KEY)
    if snapshot is None:
        storage.record_event(message.from_user.id, "weather_auto_failed", {"city": city})
        await state.set_state(OutfitForm.weather)
        await message.answer(
            "Не удалось получить погоду по этому городу 😔 Выбери вручную:",
            reply_markup=weather_keyboard(back=False),
            parse_mode="HTML",
        )
        return

    await state.update_data(weather=snapshot.bucket)
    storage.record_event(
        message.from_user.id,
        "weather_auto_succeeded",
        {"city": snapshot.city, "bucket": snapshot.bucket, "temp": snapshot.temp},
    )
    storage.record_event(message.from_user.id, "weather_selected", {"value": snapshot.bucket, "source": "auto"})
    storage.record_event(message.from_user.id, "question_answered", {"step": "weather", "value": snapshot.bucket})

    bucket_titles = {"warm": "тёплая", "mild": "переменчивая", "cold": "холодная", "rain": "дождливая"}
    bucket_label = bucket_titles.get(snapshot.bucket, snapshot.bucket)
    await message.answer(
        f"📍 <b>{snapshot.city}</b>: {snapshot.temp:+.0f}°, {snapshot.condition} → собираю на «{bucket_label}» погоду.",
        parse_mode="HTML",
    )

    data = await state.get_data()
    history = list(data.get("history", []))
    history.append("weather")
    await state.update_data(history=history)
    await state.set_state(OutfitForm.activity)
    await message.answer(
        "🗓 <b>Насколько насыщенный у тебя день?</b>",
        reply_markup=activity_keyboard(back=True),
        parse_mode="HTML",
    )


@router.callback_query(OutfitForm.activity, F.data.startswith("activity:"))
async def process_activity(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[1]  # type: ignore[union-attr]
    await state.update_data(activity=value)
    storage.record_event(callback.from_user.id, "question_answered", {"step": "activity", "value": value})
    await _show_step(callback, state, "priority", advance_from="activity")
    await callback.answer()


@router.callback_query(OutfitForm.priority, F.data.startswith("priority:"))
async def process_priority(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[1]  # type: ignore[union-attr]
    await state.update_data(priority=value)
    storage.record_event(callback.from_user.id, "question_answered", {"step": "priority", "value": value})
    await _show_step(callback, state, "mood", advance_from="priority")
    await callback.answer()


@router.callback_query(OutfitForm.mood, F.data.startswith("mood:"))
async def process_mood(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[1]  # type: ignore[union-attr]
    await state.update_data(mood=value)
    storage.record_event(callback.from_user.id, "question_answered", {"step": "mood", "value": value})
    data = await state.get_data()
    if data.get("flow_mode") == "quick" and data.get("budget") and data.get("style"):
        await _finalize_quiz(callback, state)
        return
    await _show_step(callback, state, "budget", advance_from="mood")
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
    await _show_step(callback, state, "style", advance_from="budget")
    await callback.answer()


@router.callback_query(F.data == "back")
async def on_back(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    history = list(data.get("history", []))
    if not history:
        await callback.answer("Это первый шаг, дальше некуда")
        return
    prev_step = history.pop()
    await state.update_data(history=history)
    await state.set_state(STATE_BY_STEP[prev_step])
    text, kb_fn = STEP_VIEW[prev_step]
    await callback.message.edit_text(  # type: ignore[union-attr]
        text,
        reply_markup=kb_fn(back=bool(history)),
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


@router.callback_query(
    lambda callback: callback.data
    and callback.data.startswith(
        (
            "gender:",
            "occasion:",
            "weather:",
            "activity:",
            "priority:",
            "mood:",
            "budget:",
            "style:",
        )
    )
)
async def stale_questionnaire_button(callback: CallbackQuery) -> None:
    await clear_clicked_keyboard(callback)
    await callback.answer(
        "Эта кнопка уже устарела. Продолжи с последнего сообщения бота 🙂",
        show_alert=True,
    )
