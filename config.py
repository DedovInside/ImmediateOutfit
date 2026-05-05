"""
Конфигурация бота OutfitNow.
Переменные загружаются из .env файла.
"""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    BOT_TOKEN: str = ""
    OWM_API_KEY: str = ""  # OpenWeatherMap API ключ (опционально)
    DB_PATH: str = str(Path(__file__).resolve().parent / "data" / "immediateoutfit.db")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
