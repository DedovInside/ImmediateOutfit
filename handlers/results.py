"""
Хендлеры выдачи результатов, сохранения, объяснений и проверки образа.
"""
from __future__ import annotations

from html import escape
from typing import Union

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, Message

from keyboards.inline import (
    feedback_skip_keyboard,
    final_keyboard,
    outfit_result_keyboard,
    result_feedback_keyboard,
    review_feedback_keyboard,
    start_keyboard,
    cancel_keyboard,
)
from models.states import OutfitForm
from services import storage
from services.ai_assistant import ai_review_outfit, is_ai_enabled
from services.catalog import find_outfit, get_outfits
from services.references import get_reference_images
from services.recommender import Recommendation, recommend, review_user_outfit
from handlers.ui import clear_clicked_keyboard

router = Router()
OUTFITS = get_outfits()


def _format_items(items: dict[str, str]) -> str:
    return "\n".join(f"  - <b>{name}</b>: {value}" for name, value in items.items())


def _format_reasons(reasons: list[str]) -> str:
    if not reasons:
        return ""
    return "\n".join(f"  • {reason}" for reason in reasons)


def _has_real_links(outfit) -> bool:
    return any(_is_real_purchase_link(link) for link in outfit.purchase_links)


def _is_real_purchase_link(link) -> bool:
    if link.url:
        return True
    if not link.article:
        return False
    return not link.article.upper().startswith("IO-")


def _format_palette(outfit) -> str:
    if not outfit.palette:
        return ""
    return "\n\n🎨 <b>Палитра:</b>\n" + "\n".join(f"  • {item}" for item in outfit.palette[:4])


def _format_styling_notes(outfit) -> str:
    if not outfit.styling_notes:
        return ""
    return "\n\n🧩 <b>Как носить:</b>\n" + "\n".join(f"  • {item}" for item in outfit.styling_notes[:2])


def _format_purchase_summary(outfit) -> str:
    if not _has_real_links(outfit):
        return ""
    marketplaces: list[str] = []
    for link in outfit.purchase_links:
        if not _is_real_purchase_link(link):
            continue
        marketplace = link.label.split(":", 1)[0].strip()
        if marketplace and marketplace not in marketplaces:
            marketplaces.append(marketplace)
    if not marketplaces:
        return ""
    return (
        "\n\n🛍 <b>Есть артикулы:</b> "
        f"{', '.join(marketplaces)}\n"
        "Нажми «Где искать», чтобы открыть полный список."
    )


def _format_outfit(recommendation: Recommendation, idx: int) -> str:
    outfit = recommendation.outfit
    reference_block = ""
    if outfit.reference:
        reference_block = (
            f"\n\n🖼 <b>Референс команды:</b> {outfit.reference.title}\n"
            f"{outfit.reference.description}"
        )

    return (
        f"<b>Вариант {idx} — {outfit.name}</b>\n\n"
        f"{_format_items(outfit.items)}\n\n"
        f"{outfit.description}\n\n"
        f"💡 <i>{outfit.tip}</i>\n\n"
        f"🧠 <b>Почему это подходит:</b>\n{_format_reasons(recommendation.reasons) or '  • Подобрал вариант под твой текущий запрос.'}"
        f"{_format_palette(outfit)}"
        f"{_format_styling_notes(outfit)}"
        f"{reference_block}"
        f"{_format_purchase_summary(outfit)}"
    )


async def show_results(message: Union[Message, CallbackQuery], state: FSMContext, user_id: int) -> None:
    data = await state.get_data()
    answers = {
        "gender": data.get("gender"),
        "occasion": data.get("occasion"),
        "weather": data.get("weather"),
        "activity": data.get("activity"),
        "priority": data.get("priority"),
        "mood": data.get("mood"),
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
            reply_markup=outfit_result_keyboard(
                recommendation.outfit.id,
                show_links=_has_real_links(recommendation.outfit),
            ),
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
    await clear_clicked_keyboard(callback)
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
        images = get_reference_images(outfit)
        if images:
            if len(images) == 1:
                await callback.message.answer_photo(  # type: ignore[union-attr]
                    FSInputFile(images[0]),
                    caption="Визуальный референс образа",
                )
            else:
                media = [InputMediaPhoto(media=FSInputFile(path)) for path in images]
                await callback.message.answer_media_group(media=media)  # type: ignore[union-attr]
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
    if outfit and _has_real_links(outfit):
        lines = [
            f"• <b>{link.label}</b>: {link.url or 'арт. ' + link.article}"
            for link in outfit.purchase_links
            if _is_real_purchase_link(link)
        ]
        await callback.message.answer(  # type: ignore[union-attr]
            "🛍 <b>Где искать вещи из образа:</b>\n\n" + "\n".join(lines),
            parse_mode="HTML",
        )
    else:
        await callback.message.answer(  # type: ignore[union-attr]
            "Для этого варианта команда пока не добавила готовые ссылки. Ориентируйся на тип вещи и собери аналог из того, что уже есть в гардеробе.",
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == "show_saved")
async def on_show_saved(callback: CallbackQuery) -> None:
    await clear_clicked_keyboard(callback)
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
    await clear_clicked_keyboard(callback)
    await callback.message.answer(  # type: ignore[union-attr]
        "🔍 <b>Проверка образа</b>\n\n"
        "Опиши, что ты планируешь надеть, а я скажу:\n"
        "- что уже хорошо\n"
        "- что спорно\n"
        "- чем можно усилить образ\n\n"
        "✍️ Пример: <i>черная водолазка, голубые джинсы, белые кеды</i>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(OutfitForm.check_outfit)
async def process_check_outfit(message: Message, state: FSMContext) -> None:
    user_text = message.text or ""
    fallback_review = review_user_outfit(user_text)
    if fallback_review.needs_more_input:
        text = (
            f"🔎 <b>{fallback_review.headline}</b>\n"
            f"Оценка: <b>{fallback_review.score_label}</b>\n\n"
            f"<b>Что не хватает:</b>\n" + "\n".join(f"• {item}" for item in fallback_review.concerns) + "\n\n"
            f"<b>Как описать:</b>\n" + "\n".join(f"• {item}" for item in fallback_review.suggestions)
        )
        await message.answer(text, parse_mode="HTML", reply_markup=cancel_keyboard())
        return

    profile = storage.get_profile(message.from_user.id)
    ai_review = await ai_review_outfit(user_text, profile) if is_ai_enabled() else None
    review = ai_review or fallback_review
    storage.record_event(
        message.from_user.id,
        "review_completed",
        {"source": "deepseek" if ai_review else "rule_based"},
    )
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


async def _maybe_request_feedback_comment(
    callback: CallbackQuery, state: FSMContext, score: int, kind: str
) -> None:
    """Если оценка низкая — спросить опциональный комментарий «что не зашло»."""
    if score >= 5:
        return
    await state.set_state(OutfitForm.feedback_comment)
    await state.update_data(feedback_kind=kind, feedback_score=score)
    prompt = (
        "Спасибо! Если коротко — <b>что не зашло?</b>\n"
        "Можно одной фразой. Или нажми «Пропустить» / отправь /skip."
    )
    await callback.message.answer(prompt, parse_mode="HTML", reply_markup=feedback_skip_keyboard())  # type: ignore[union-attr]


@router.callback_query(F.data.startswith("result_feedback:"))
async def result_feedback(callback: CallbackQuery, state: FSMContext) -> None:
    score = int(callback.data.split(":")[1])  # type: ignore[union-attr]
    storage.record_event(callback.from_user.id, "result_feedback", {"score": score})
    await clear_clicked_keyboard(callback)
    await callback.answer("Спасибо, это поможет нам улучшать подбор.")
    await _maybe_request_feedback_comment(callback, state, score, "result")


@router.callback_query(F.data.startswith("review_feedback:"))
async def review_feedback(callback: CallbackQuery, state: FSMContext) -> None:
    score = int(callback.data.split(":")[1])  # type: ignore[union-attr]
    storage.record_event(callback.from_user.id, "review_feedback", {"score": score})
    await clear_clicked_keyboard(callback)
    await callback.answer("Спасибо за оценку разбора.")
    await _maybe_request_feedback_comment(callback, state, score, "review")


@router.message(OutfitForm.feedback_comment, Command("skip"))
async def feedback_comment_skip_cmd(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Окей, пропустил 👍")


@router.callback_query(OutfitForm.feedback_comment, F.data == "feedback_comment_skip")
async def feedback_comment_skip_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Окей, пропустил")
    await callback.message.edit_reply_markup(reply_markup=None)  # type: ignore[union-attr]


@router.message(OutfitForm.feedback_comment)
async def feedback_comment_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    kind = data.get("feedback_kind", "result")
    score = data.get("feedback_score")
    text = (message.text or "").strip()[:500]
    if not text:
        await message.answer("Кажется, ничего не отправилось. Попробуй ещё раз или нажми /skip.")
        return
    event_name = f"{kind}_feedback_comment"
    storage.record_event(message.from_user.id, event_name, {"score": score, "text": text})
    await state.clear()
    await message.answer(f"🙏 Спасибо за комментарий: <i>«{escape(text)}»</i>", parse_mode="HTML")
