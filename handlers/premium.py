"""
Premium-заглушка и сбор интереса к монетизации.
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from keyboards.inline import premium_keyboard
from services import storage
from handlers.ui import cleanup_tracked_messages, clear_clicked_keyboard, send_tracked_message

router = Router()

PREMIUM_TEXT = (
    "✨ <b>ImmediateOutfit Premium</b>\n\n"
    "Сейчас в бесплатном режиме доступно несколько AI-ответов, чтобы попробовать сценарии "
    "«Под мою вещь» и «Проверить мой образ».\n\n"
    "Premium будет нужен для увеличенных лимитов AI-стилиста и будущих расширенных функций:\n"
    "- недельные подборки образов\n"
    "- расширенный профиль и более точный подбор\n"
    "- разбор гардероба и персональные рекомендации\n"
    "- photo-review образа как experimental-функция\n\n"
    "Платёжный контур планируем через Telegram Stars. Сейчас можно оставить интерес к early access."
)


@router.callback_query(F.data == "premium_info")
async def premium_info(callback: CallbackQuery, state: FSMContext) -> None:
    await cleanup_tracked_messages(callback)
    await state.clear()
    storage.record_event(callback.from_user.id, "premium_viewed")
    await clear_clicked_keyboard(callback)
    await send_tracked_message(callback.message, callback.from_user.id, PREMIUM_TEXT, parse_mode="HTML", reply_markup=premium_keyboard())  # type: ignore[arg-type]
    await callback.answer()


@router.callback_query(F.data == "premium_interest")
async def premium_interest(callback: CallbackQuery) -> None:
    storage.record_event(callback.from_user.id, "premium_interest")
    await clear_clicked_keyboard(callback)
    await send_tracked_message(  # type: ignore[arg-type]
        callback.message,
        callback.from_user.id,
        "Готово, записал интерес к Premium ✨\n\n"
        "Когда откроем расширенные AI-лимиты и новые функции, это будет первым сигналом для запуска.",
        parse_mode="HTML",
    )
    await callback.answer("Интерес к Premium записан.", show_alert=True)
