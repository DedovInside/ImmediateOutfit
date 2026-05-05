"""
Хендлеры выдачи результатов, сохранения, объяснений и проверки образа.
"""
from __future__ import annotations

from typing import Union

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.inline import (
    final_keyboard,
    outfit_result_keyboard,
    result_feedback_keyboard,
    review_feedback_keyboard,
    start_keyboard,
)
from models.states import OutfitForm
from services import storage
from services.catalog import find_outfit, get_outfits
from services.recommender import Recommendation, recommend, review_user_outfit

router = Router()
OUTFITS = get_outfits()


def _format_items(items: dict[str, str]) -> str:
    return "\n".join(f"  - <b>{name}</b>: {value}" for name, value in items.items())


def _format_reasons(reasons: list[str]) -> str:
    if not reasons:
        return ""
    return "\n".join(f"  • {reason}" for reason in reasons)


def _format_outfit(recommendation: Recommendation, idx: int) -> str:
    outfit = recommendation.outfit
    reference_block = ""
    if outfit.reference:
        reference_block = (
            f"\n\n🖼 <b>Референс команды:</b> {outfit.reference.title}\n"
            f"{outfit.reference.description}"
        )

    links_block = ""
    if outfit.purchase_links:
        prepared = []
        for link in outfit.purchase_links:
            if link.article:
                prepared.append(f"{link.label}: артикул <code>{link.article}</code>")
            elif link.url:
                prepared.append(f"{link.label}: {link.url}")
            else:
                prepared.append(link.label)
        links_block = "\n\n🛍 <b>Что можно докупить:</b>\n" + "\n".join(f"  • {item}" for item in prepared)

    return (
        f"<b>Вариант {idx} — {outfit.name}</b>\n\n"
        f"{_format_items(outfit.items)}\n\n"
        f"{outfit.description}\n\n"
        f"💡 <i>{outfit.tip}</i>\n\n"
        f"🧠 <b>Почему это подходит:</b>\n{_format_reasons(recommendation.reasons) or '  • Подобрал вариант под твой текущий запрос.'}"
        f"{reference_block}"
        f"{links_block}"
    )


async def show_results(message: Union[Message, CallbackQuery], state: FSMContext, user_id: int) -> None:
    data = await state.get_data()
    answers = {
        "gender": data.get("gender"),
        "occasion": data.get("occasion"),
        "weather": data.get("weather"),
        "activity": data.get("activity"),
        "priority": data.get("priority"),
        "budget": data.get("budget"),
        "style": data.get("style"),
    }
    shown_ids: list[str] = data.get("shown_ids", [])
    item_anchor: str | None = data.get("item_anchor")
    profile = storage.get_profile(user_id)
    results = recommend(
        answers=answers,
        outfits=OUTFITS,
        shown_ids=shown_ids,
        profile=profile,
        item_anchor=item_anchor,
        limit=2,
    )

    target = message if isinstance(message, Message) else message.message
    if not results:
        await target.answer(  # type: ignore[union-attr]
            "Пока не вижу ещё новых подходящих вариантов 😅\nПопробуй поменять параметры или обновить профиль.",
            reply_markup=final_keyboard(),
            parse_mode="HTML",
        )
        return

    new_shown = shown_ids + [item.outfit.id for item in results]
    await state.update_data(
        shown_ids=new_shown,
        last_outfits=[item.outfit.id for item in results],
        last_reasons={item.outfit.id: item.reasons for item in results},
    )
    storage.record_event(user_id, "results_viewed", {"count": len(results), "flow_mode": data.get("flow_mode", "standard")})

    for idx, recommendation in enumerate(results, start=1):
        await target.answer(  # type: ignore[union-attr]
            _format_outfit(recommendation, idx),
            reply_markup=outfit_result_keyboard(recommendation.outfit.id),
            parse_mode="HTML",
        )

    await target.answer(  # type: ignore[union-attr]
        "Если сомневаешься, сначала бери тот вариант, который проще реализовать из твоего шкафа.",
        reply_markup=result_feedback_keyboard(),
        parse_mode="HTML",
    )
    await target.answer(  # type: ignore[union-attr]
        "Можем продолжить: показать ещё, собрать под твою вещь или сохранить удачные варианты.",
        reply_markup=final_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "show_more")
async def on_show_more(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(OutfitForm.result)
    storage.record_event(callback.from_user.id, "show_more")
    await show_results(callback, state, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data.startswith("save:"))
async def on_save(callback: CallbackQuery, state: FSMContext) -> None:
    outfit_id = callback.data.split(":")[1]  # type: ignore[union-attr]
    outfit = find_outfit(outfit_id)
    if outfit and storage.save_outfit(callback.from_user.id, outfit):
        await callback.answer("✅ Образ сохранён!", show_alert=True)
    elif outfit:
        await callback.answer("Этот образ уже сохранён 😉", show_alert=True)
    else:
        await callback.answer("Не удалось найти образ", show_alert=True)


@router.callback_query(F.data.startswith("explain:"))
async def on_explain(callback: CallbackQuery, state: FSMContext) -> None:
    outfit_id = callback.data.split(":")[1]  # type: ignore[union-attr]
    data = await state.get_data()
    reasons = (data.get("last_reasons") or {}).get(outfit_id, [])
    storage.record_event(callback.from_user.id, "explanation_opened", {"outfit_id": outfit_id})
    text = "🧠 <b>Почему этот вариант стоит рассмотреть:</b>\n\n"
    if reasons:
        text += "\n".join(f"• {reason}" for reason in reasons)
    else:
        text += "• Он близок к твоим ответам по стилю, формату дня и уровню комфорта."
    await callback.message.answer(text, parse_mode="HTML")  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data.startswith("reference:"))
async def on_reference(callback: CallbackQuery) -> None:
    outfit_id = callback.data.split(":")[1]  # type: ignore[union-attr]
    outfit = find_outfit(outfit_id)
    storage.record_event(callback.from_user.id, "reference_opened", {"outfit_id": outfit_id})
    if outfit and outfit.reference:
        text = (
            f"🖼 <b>{outfit.reference.title}</b>\n\n"
            f"{outfit.reference.description}"
        )
        if outfit.reference.image_url:
            text += f"\n\nСсылка на референс: {outfit.reference.image_url}"
        await callback.message.answer(text, parse_mode="HTML")  # type: ignore[union-attr]
    else:
        await callback.message.answer(  # type: ignore[union-attr]
            "Для этого образа пока нет отдельного визуального референса, но каркас образа уже можно собрать по списку вещей.",
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data.startswith("links:"))
async def on_links(callback: CallbackQuery) -> None:
    outfit_id = callback.data.split(":")[1]  # type: ignore[union-attr]
    outfit = find_outfit(outfit_id)
    storage.record_event(callback.from_user.id, "links_opened", {"outfit_id": outfit_id})
    if outfit and outfit.purchase_links:
        lines = []
        for link in outfit.purchase_links:
            if link.article:
                lines.append(f"• <b>{link.label}</b>: артикул <code>{link.article}</code>")
            elif link.url:
                lines.append(f"• <b>{link.label}</b>: {link.url}")
            else:
                lines.append(f"• <b>{link.label}</b>")
        await callback.message.answer(  # type: ignore[union-attr]
            "🛍 <b>Ссылки и артикулы для образа:</b>\n\n" + "\n".join(lines),
            parse_mode="HTML",
        )
    else:
        await callback.message.answer(  # type: ignore[union-attr]
            "Для этого варианта команда пока не добавила артикулы. Можно ориентироваться на тип вещи и собрать аналог из того, что уже есть.",
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == "show_saved")
async def on_show_saved(callback: CallbackQuery) -> None:
    saved = storage.get_saved(callback.from_user.id)
    if not saved:
        await callback.answer("У тебя пока нет сохранённых образов 🤷", show_alert=True)
        return

    lines = []
    for index, outfit in enumerate(saved, start=1):
        items_str = ", ".join(outfit.items.values())
        lines.append(f"<b>{index}. {outfit.name}</b>\n   {items_str}")

    await callback.message.answer(  # type: ignore[union-attr]
        "📂 <b>Твои сохранённые образы:</b>\n\n" + "\n\n".join(lines),
        parse_mode="HTML",
        reply_markup=start_keyboard(has_profile=storage.get_profile(callback.from_user.id) is not None),
    )
    await callback.answer()


@router.callback_query(F.data == "check_outfit")
async def on_check_outfit(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(OutfitForm.check_outfit)
    storage.record_event(callback.from_user.id, "review_started")
    await callback.message.answer(  # type: ignore[union-attr]
        "🔍 <b>Проверка образа</b>\n\n"
        "Опиши, что ты планируешь надеть, а я скажу:\n"
        "- что уже хорошо\n"
        "- что спорно\n"
        "- чем можно усилить образ\n\n"
        "✍️ Пример: <i>черная водолазка, голубые джинсы, белые кеды</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(OutfitForm.check_outfit)
async def process_check_outfit(message: Message, state: FSMContext) -> None:
    review = review_user_outfit(message.text or "")
    storage.record_event(message.from_user.id, "review_completed")
    text = (
        f"🔎 <b>{review.headline}</b>\n"
        f"Оценка: <b>{review.score_label}</b>\n\n"
        f"<b>Что уже хорошо:</b>\n" + "\n".join(f"• {item}" for item in review.strengths) + "\n\n"
        f"<b>Что спорно:</b>\n" + "\n".join(f"• {item}" for item in review.concerns) + "\n\n"
        f"<b>Как усилить:</b>\n" + "\n".join(f"• {item}" for item in review.suggestions)
    )
    await message.answer(text, parse_mode="HTML", reply_markup=review_feedback_keyboard())
    await message.answer(
        "Если хочешь, после этого могу сразу собрать для тебя альтернативный образ под ту же ситуацию.",
        reply_markup=final_keyboard(),
        parse_mode="HTML",
    )
    await state.clear()


@router.callback_query(F.data.startswith("result_feedback:"))
async def result_feedback(callback: CallbackQuery) -> None:
    score = int(callback.data.split(":")[1])  # type: ignore[union-attr]
    storage.record_event(callback.from_user.id, "result_feedback", {"score": score})
    await callback.answer("Спасибо, это поможет нам улучшать подбор.")


@router.callback_query(F.data.startswith("review_feedback:"))
async def review_feedback(callback: CallbackQuery) -> None:
    score = int(callback.data.split(":")[1])  # type: ignore[union-attr]
    storage.record_event(callback.from_user.id, "review_feedback", {"score": score})
    await callback.answer("Спасибо за оценку разбора.")
