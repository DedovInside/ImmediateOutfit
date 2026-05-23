"""
Небольшие UI-хелперы для Telegram-сообщений.
"""
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest


async def clear_clicked_keyboard(callback: CallbackQuery) -> None:
    """Убирает inline-клавиатуру у сообщения, по которому только что кликнули."""
    if not callback.message:
        return
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        # Сообщение могло быть уже изменено/без клавиатуры; это не должно ломать сценарий.
        return
