"""
Хендлеры профиля и пользовательских предпочтений.
"""
from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.inline import cancel_keyboard, profile_keyboard
from models.states import OutfitForm
from services import storage
from handlers.ui import clear_clicked_keyboard

router = Router()

GENDER_LABELS = {"male": "парень", "female": "девушка"}
STYLE_LABELS = {
    "base_minimal": "база / минимализм",
    "casual": "casual",
    "sport": "спорт",
    "classic": "классика",
}
BUDGET_LABELS = {"low": "экономно", "medium": "средний", "high": "можно вложиться"}


def _label(value: str | None, mapping: dict[str, str]) -> str:
    if not value:
        return "не указан"
    return escape(mapping.get(value, value))


def _join_user_list(items: list[str], empty_text: str) -> str:
    if not items:
        return empty_text
    return ", ".join(escape(item) for item in items)


def _format_profile(user_id: int) -> str:
    profile = storage.get_profile(user_id)
    if not profile:
        return (
            "🧬 <b>Профиль пока пустой.</b>\n\n"
            "Сохрани хотя бы стиль, бюджет и пару любимых цветов — тогда быстрый подбор станет заметно точнее."
        )

    return (
        "🧬 <b>Твой профиль ImmediateOutfit</b>\n\n"
        f"Пол: <b>{_label(profile.gender, GENDER_LABELS)}</b>\n"
        f"Стиль: <b>{_label(profile.style, STYLE_LABELS)}</b>\n"
        f"Бюджет: <b>{_label(profile.budget, BUDGET_LABELS)}</b>\n"
        f"Любимые цвета: <b>{_join_user_list(profile.preferred_colors, 'не заданы')}</b>\n"
        f"Анти-предпочтения: <b>{_join_user_list(profile.disliked_items, 'не заданы')}</b>\n"
        f"Ключевые вещи: <b>{_join_user_list(profile.key_items, 'не заданы')}</b>"
    )


@router.callback_query(F.data == "profile_view")
async def profile_view(callback: CallbackQuery) -> None:
    storage.record_event(callback.from_user.id, "profile_viewed")
    has_profile = storage.get_profile(callback.from_user.id) is not None
    await clear_clicked_keyboard(callback)
    await callback.message.answer(  # type: ignore[union-attr]
        _format_profile(callback.from_user.id),
        parse_mode="HTML",
        reply_markup=profile_keyboard(has_profile=has_profile),
    )
    await callback.answer()


@router.callback_query(F.data == "profile_colors")
async def profile_colors(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(OutfitForm.profile_colors)
    await clear_clicked_keyboard(callback)
    await callback.message.answer(  # type: ignore[union-attr]
        "🎨 <b>Напиши любимые цвета через запятую.</b>\n\n"
        "Например: <i>черный, белый, серый, бежевый</i>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(OutfitForm.profile_colors)
async def save_profile_colors(message: Message, state: FSMContext) -> None:
    colors = [item.strip() for item in (message.text or "").split(",") if item.strip()]
    storage.upsert_profile(message.from_user.id, preferred_colors=colors)
    await message.answer(
        "Сохранил цвета. Теперь бот сможет учитывать их при подборе.",
        parse_mode="HTML",
        reply_markup=profile_keyboard(has_profile=True),
    )
    await state.clear()


@router.callback_query(F.data == "profile_disliked")
async def profile_disliked(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(OutfitForm.profile_disliked)
    await clear_clicked_keyboard(callback)
    await callback.message.answer(  # type: ignore[union-attr]
        "🚫 <b>Напиши вещи или типы вещей, которые не любишь носить.</b>\n\n"
        "Например: <i>каблуки, оверсайз худи, короткие юбки</i>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(OutfitForm.profile_disliked)
async def save_profile_disliked(message: Message, state: FSMContext) -> None:
    disliked = [item.strip() for item in (message.text or "").split(",") if item.strip()]
    storage.upsert_profile(message.from_user.id, disliked_items=disliked)
    await message.answer(
        "Запомнил анти-предпочтения.",
        parse_mode="HTML",
        reply_markup=profile_keyboard(has_profile=True),
    )
    await state.clear()


@router.callback_query(F.data == "profile_key_items")
async def profile_key_items(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(OutfitForm.profile_key_items)
    await clear_clicked_keyboard(callback)
    await callback.message.answer(  # type: ignore[union-attr]
        "👕 <b>Напиши ключевые вещи из твоего шкафа через запятую.</b>\n\n"
        "Например: <i>белая рубашка, черные прямые брюки, голубые джинсы</i>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(OutfitForm.profile_key_items)
async def save_profile_key_items(message: Message, state: FSMContext) -> None:
    key_items = [item.strip() for item in (message.text or "").split(",") if item.strip()]
    storage.upsert_profile(message.from_user.id, key_items=key_items)
    await message.answer(
        "Ключевые вещи сохранены. Теперь бот сможет чаще подбирать образы под них.",
        parse_mode="HTML",
        reply_markup=profile_keyboard(has_profile=True),
    )
    await state.clear()
