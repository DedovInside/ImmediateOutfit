"""
Конфигурация бота OutfitNow.
Переменные загружаются из .env файла.
"""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    BOT_TOKEN: str = ""
    OWM_API_KEY: str = ""  # OpenWeatherMap API ключ (опционально)
    AI_ENABLED: bool = False
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-v4-flash"
    DEEPSEEK_TIMEOUT_SECONDS: int = 15
    AI_FREE_LIMIT: int = 5
    DB_PATH: str = str(Path(__file__).resolve().parent / "data" / "immediateoutfit.db")
    DEMO_SEED_ON_START: bool = False
    DEMO_XLSX_PATH: str = str(
        Path(r"C:\Users\johnn\Downloads\Telegram Desktop\ImmediateOutfit_AARRR_dataset.xlsx")
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
