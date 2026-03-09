"""
Хендлеры показа результатов, сохранения, «Показать ещё», «Проверить мой образ».
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Union

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from models.outfit import Outfit
from models.states import OutfitForm
from keyboards.inline import outfit_result_keyboard, final_keyboard, start_keyboard
from services.recommender import recommend, check_user_outfit
from services import storage

router = Router()

# Загрузка базы образов
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "outfits.json"

def _load_outfits() -> list[Outfit]:
    with open(DATA_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    return [Outfit(**item) for item in raw]

OUTFITS = _load_outfits()


# Формирование текстового сообщения образа
def _format_outfit(outfit: Outfit, idx: int) -> str:
    items_lines = "\n".join(f"  - <b>{k}</b>: {v}" for k, v in outfit.items.items())
    return (
        f"<b>Вариант {idx} - {outfit.name}</b>\n\n"
        f"{items_lines}\n\n"
        f"{outfit.description}\n\n"
        f"💡 <i>{outfit.tip}</i>"
    )


# Показ результатов (вызывается из questionnaire)
async def show_results(message: Union[Message, CallbackQuery], state: FSMContext) -> None:
    """Отправляет 1-2 подобранных образа."""
    data = await state.get_data()
    answers = {
        "gender": data.get("gender"),
        "occasion": data.get("occasion"),
        "activity": data.get("activity"),
        "priority": data.get("priority"),
        "style": data.get("style"),
    }
    shown_ids: list[str] = data.get("shown_ids", [])

    results = recommend(answers, OUTFITS, shown_ids=shown_ids)

    if not results:
        target = message if isinstance(message, Message) else message.message
        await target.answer(  # type: ignore[union-attr]
            "К сожалению, я больше не могу предложить новых вариантов 😅\n"
            "Попробуй изменить параметры!",
            reply_markup=final_keyboard(),
            parse_mode="HTML",
        )
        return

    # Обновляем shown_ids
    new_shown = shown_ids + [o.id for o in results]
    await state.update_data(shown_ids=new_shown, last_outfits=[o.model_dump() for o in results])

    target = message if isinstance(message, Message) else message.message

    for idx, outfit in enumerate(results, start=1):
        text = _format_outfit(outfit, idx)
        kb = outfit_result_keyboard(outfit.id)
        await target.answer(text, reply_markup=kb, parse_mode="HTML")  # type: ignore[union-attr]

    # Финальная подсказка
    if len(results) >= 1:
        await target.answer(  # type: ignore[union-attr]
            "Если сомневаешься - выбирай первый вариант, он самый универсальный 👍",
            reply_markup=final_keyboard(),
            parse_mode="HTML",
        )


# Callback: «Показать ещё»
@router.callback_query(F.data == "show_more")
async def on_show_more(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(OutfitForm.result)
    await show_results(callback, state)
    await callback.answer()


# Callback: «Подходит» (сохранить)
@router.callback_query(F.data.startswith("save:"))
async def on_save(callback: CallbackQuery, state: FSMContext) -> None:
    outfit_id = callback.data.split(":")[1]  # type: ignore[union-attr]
    outfit = next((o for o in OUTFITS if o.id == outfit_id), None)
    user_id = callback.from_user.id

    if outfit:
        saved = storage.save_outfit(user_id, outfit)
        if saved:
            await callback.answer("✅ Образ сохранён!", show_alert=True)
        else:
            await callback.answer("Этот образ уже сохранён 😉", show_alert=True)
    else:
        await callback.answer("Не удалось найти образ", show_alert=True)


# Callback: «Мои сохранённые»
@router.callback_query(F.data == "show_saved")
async def on_show_saved(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = callback.from_user.id
    saved = storage.get_saved(user_id)

    if not saved:
        await callback.answer("У тебя пока нет сохранённых образов 🤷", show_alert=True)
        return

    lines = []
    for i, outfit in enumerate(saved, start=1):
        items_str = ", ".join(outfit.items.values())
        lines.append(f"<b>{i}. {outfit.name}</b>\n   {items_str}")

    text = "📂 <b>Твои сохранённые образы:</b>\n\n" + "\n\n".join(lines)
    await callback.message.answer(text, parse_mode="HTML", reply_markup=start_keyboard())  # type: ignore[union-attr]
    await callback.answer()


# Callback: «Проверить мой образ»
@router.callback_query(F.data == "check_outfit")
async def on_check_outfit(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(OutfitForm.check_outfit)
    await callback.message.answer(  # type: ignore[union-attr]
        "🔍 <b>Проверка образа</b>\n\n"
        "Уже знаешь, что наденешь, но хочешь убедиться что это удачно? "
        "Опиши свой образ - я скажу, насколько он уместен и дам совет по улучшению.\n\n"
        "✍️ Напиши, что планируешь надеть:\n"
        "<i>Например: «чёрная водолазка, джинсы, кроссовки»</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(OutfitForm.check_outfit)
async def process_check_outfit(message: Message, state: FSMContext) -> None:
    text = message.text or ""
    result = check_user_outfit(text, OUTFITS)
    await message.answer(result, reply_markup=start_keyboard(), parse_mode="HTML")
    await state.clear()