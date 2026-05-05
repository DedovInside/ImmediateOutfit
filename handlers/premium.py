"""
Premium-заглушка и сбор интереса к монетизации.
"""
from aiogram import F, Router
from aiogram.types import CallbackQuery

from keyboards.inline import premium_keyboard
from services import storage

router = Router()

PREMIUM_TEXT = (
    "✨ <b>ImmediateOutfit Premium</b>\n\n"
    "Что хотим валидировать как premium:\n"
    "- недельные подборки образов\n"
    "- расширенный профиль и более точный подбор\n"
    "- разбор гардероба и персональные рекомендации\n"
    "- photo-review образа как experimental-функция\n\n"
    "Сейчас это ещё не боевой платежный контур, а продуктовый тест на интерес."
)


@router.callback_query(F.data == "premium_info")
async def premium_info(callback: CallbackQuery) -> None:
    storage.record_event(callback.from_user.id, "premium_viewed")
    await callback.message.answer(PREMIUM_TEXT, parse_mode="HTML", reply_markup=premium_keyboard())  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data == "premium_interest")
async def premium_interest(callback: CallbackQuery) -> None:
    storage.record_event(callback.from_user.id, "premium_interest")
    await callback.answer("Супер, записал твой интерес к premium.", show_alert=True)
