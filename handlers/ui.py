"""
Небольшие UI-хелперы для Telegram-сообщений.
"""
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from services import storage


async def clear_clicked_keyboard(callback: CallbackQuery) -> None:
    """Убирает inline-клавиатуру у сообщения, по которому только что кликнули."""
    if not callback.message:
        return
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        # Сообщение могло быть уже изменено/без клавиатуры; это не должно ломать сценарий.
        return


async def track_message(user_id: int, message) -> None:
    """Запоминает сообщение бота, чтобы потом можно было подчистить чат."""
    if message:
        storage.track_bot_message(user_id, message.chat.id, message.message_id)


async def send_tracked_message(target, user_id: int, *args, **kwargs):
    """Отправляет сообщение и запоминает его message_id."""
    sent = await target.answer(*args, **kwargs)
    await track_message(user_id, sent)
    return sent


async def cleanup_tracked_messages(callback: CallbackQuery) -> None:
    """Удаляет ранее отправленные сообщения бота, которые были сохранены в SQLite."""
    if not callback.message:
        return
    user_id = callback.from_user.id
    current_chat_id = callback.message.chat.id
    current_message_id = callback.message.message_id
    for item in storage.get_tracked_bot_messages(user_id):
        if item["chat_id"] == current_chat_id and item["message_id"] == current_message_id:
            continue
        try:
            await callback.bot.delete_message(
                chat_id=item["chat_id"],
                message_id=item["message_id"],
            )
        except TelegramBadRequest:
            pass
    storage.clear_tracked_bot_messages(user_id)


async def cleanup_tracked_messages_for_message(message) -> None:
    """То же самое для команд вроде /start, где нет callback."""
    user_id = message.from_user.id
    for item in storage.get_tracked_bot_messages(user_id):
        try:
            await message.bot.delete_message(
                chat_id=item["chat_id"],
                message_id=item["message_id"],
            )
        except TelegramBadRequest:
            pass
    storage.clear_tracked_bot_messages(user_id)
