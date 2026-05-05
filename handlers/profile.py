"""
Хендлеры профиля и пользовательских предпочтений.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.inline import profile_keyboard
from models.states import OutfitForm
from services import storage

router = Router()


def _format_profile(user_id: int) -> str:
    profile = storage.get_profile(user_id)
    if not profile:
        return (
            "🧬 <b>Профиль пока пустой.</b>\n\n"
            "Сохрани хотя бы стиль, бюджет и пару любимых цветов — тогда быстрый подбор станет заметно точнее."
        )

    return (
        "🧬 <b>Твой профиль ImmediateOutfit</b>\n\n"
        f"Пол: <b>{profile.gender or 'не указан'}</b>\n"
        f"Стиль: <b>{profile.style or 'не указан'}</b>\n"
        f"Бюджет: <b>{profile.budget or 'не указан'}</b>\n"
        f"Любимые цвета: <b>{', '.join(profile.preferred_colors) or 'не заданы'}</b>\n"
        f"Анти-предпочтения: <b>{', '.join(profile.disliked_items) or 'не заданы'}</b>\n"
        f"Ключевые вещи: <b>{', '.join(profile.key_items) or 'не заданы'}</b>"
    )


@router.callback_query(F.data == "profile_view")
async def profile_view(callback: CallbackQuery) -> None:
    storage.record_event(callback.from_user.id, "profile_viewed")
    has_profile = storage.get_profile(callback.from_user.id) is not None
    await callback.message.answer(  # type: ignore[union-attr]
        _format_profile(callback.from_user.id),
        parse_mode="HTML",
        reply_markup=profile_keyboard(has_profile=has_profile),
    )
    await callback.answer()


@router.callback_query(F.data == "profile_colors")
async def profile_colors(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(OutfitForm.profile_colors)
    await callback.message.answer(  # type: ignore[union-attr]
        "🎨 <b>Напиши любимые цвета через запятую.</b>\n\n"
        "Например: <i>черный, белый, серый, бежевый</i>",
        parse_mode="HTML",
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
    await callback.message.answer(  # type: ignore[union-attr]
        "🚫 <b>Напиши вещи или типы вещей, которые не любишь носить.</b>\n\n"
        "Например: <i>каблуки, оверсайз худи, короткие юбки</i>",
        parse_mode="HTML",
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
    await callback.message.answer(  # type: ignore[union-attr]
        "👕 <b>Напиши ключевые вещи из твоего шкафа через запятую.</b>\n\n"
        "Например: <i>белая рубашка, черные прямые брюки, голубые джинсы</i>",
        parse_mode="HTML",
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
