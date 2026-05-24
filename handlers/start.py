"""
Стартовые сценарии и главное меню.
"""
from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.inline import start_keyboard
from services import storage
from handlers.ui import (
    cleanup_tracked_messages,
    cleanup_tracked_messages_for_message,
    clear_clicked_keyboard,
    send_tracked_message,
)

router = Router()

WELCOME_TEXT = (
    "Привет! 👋 Я помогу тебе быстро выбрать образ на день и не зависнуть перед шкафом.\n\n"
    "Что умею уже сейчас:\n"
    "- подобрать образ под событие, погоду и твой приоритет\n"
    "- собрать образ вокруг вещи, которая у тебя уже есть\n"
    "- проверить твой текущий лук и подсказать, как его усилить\n"
    "- запомнить предпочтения для более быстрого подбора\n\n"
    "Выбирай сценарий ниже."
)


def _menu_keyboard(user_id: int):
    profile = storage.get_profile(user_id)
    return start_keyboard(has_profile=profile is not None)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await cleanup_tracked_messages_for_message(message)
    await state.clear()
    storage.touch_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )
    storage.record_event(message.from_user.id, "bot_started")
    await send_tracked_message(
        message,
        message.from_user.id,
        WELCOME_TEXT,
        reply_markup=_menu_keyboard(message.from_user.id),
    )


@router.callback_query(F.data == "menu_home")
async def menu_home(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cleanup_tracked_messages(callback)
    await clear_clicked_keyboard(callback)
    await send_tracked_message(  # type: ignore[arg-type]
        callback.message,
        callback.from_user.id,
        WELCOME_TEXT,
        reply_markup=_menu_keyboard(callback.from_user.id),
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_flow")
async def cancel_flow(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cleanup_tracked_messages(callback)
    await clear_clicked_keyboard(callback)
    storage.record_event(callback.from_user.id, "flow_cancelled")
    await send_tracked_message(  # type: ignore[arg-type]
        callback.message,
        callback.from_user.id,
        "Окей, отменил текущий сценарий. Возвращаю в главное меню.",
        reply_markup=_menu_keyboard(callback.from_user.id),
    )
    await callback.answer()
