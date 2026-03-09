"""
OutfitNow - Telegram-бот для подбора образа.
Точка входа: python bot.py
"""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from handlers import start, questionnaire, results


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )

    if not settings.BOT_TOKEN or settings.BOT_TOKEN == "ВАШ_ТОКЕН_БОТА":
        logging.error(
            "❌ BOT_TOKEN не задан! "
            "Создайте файл .env и укажите BOT_TOKEN=<ваш токен от @BotFather>"
        )
        sys.exit(1)

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрация роутеров
    dp.include_router(start.router)
    dp.include_router(questionnaire.router)
    dp.include_router(results.router)

    logging.info("🚀 Бот OutfitNow запущен!")

    # Удаляем pending updates и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

