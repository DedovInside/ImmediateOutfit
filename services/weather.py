"""
Интеграция с OpenWeatherMap для авто-определения погоды по городу.
Чистая функция temp_to_bucket вынесена отдельно для тестирования без сети.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

OWM_URL = "https://api.openweathermap.org/data/2.5/weather"
TIMEOUT_SECONDS = 5
CACHE_TTL_SECONDS = 600  # 10 минут


@dataclass(frozen=True)
class WeatherSnapshot:
    city: str
    temp: float
    condition: str  # человекочитаемое описание из OWM (e.g. "переменная облачность")
    bucket: str  # warm / mild / cold / rain


def temp_to_bucket(temp: float, condition_main: str) -> str:
    """Мапим температуру + main-условие OWM в наш ручной bucket."""
    if condition_main.lower() in {"rain", "drizzle", "thunderstorm", "snow"}:
        return "rain"
    if temp >= 18:
        return "warm"
    if temp >= 10:
        return "mild"
    return "cold"


_cache: dict[str, tuple[WeatherSnapshot, float]] = {}


def _cache_get(city_key: str) -> WeatherSnapshot | None:
    entry = _cache.get(city_key)
    if not entry:
        return None
    snapshot, ts = entry
    if time.time() - ts > CACHE_TTL_SECONDS:
        _cache.pop(city_key, None)
        return None
    return snapshot


def _cache_set(city_key: str, snapshot: WeatherSnapshot) -> None:
    _cache[city_key] = (snapshot, time.time())


async def fetch_weather(city: str, api_key: str) -> WeatherSnapshot | None:
    """Возвращает WeatherSnapshot или None при любой ошибке."""
    try:
        import aiohttp
    except ImportError:
        return None

    if not city.strip() or not api_key:
        return None
    city_key = city.strip().lower()
    cached = _cache_get(city_key)
    if cached:
        return cached

    params = {
        "q": city.strip(),
        "appid": api_key,
        "units": "metric",
        "lang": "ru",
    }
    timeout = aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(OWM_URL, params=params) as response:
                if response.status != 200:
                    return None
                data = await response.json()
    except (aiohttp.ClientError, TimeoutError):
        return None

    try:
        temp = float(data["main"]["temp"])
        weather_main = data["weather"][0]["main"]
        condition_desc = data["weather"][0].get("description", weather_main)
        resolved_name = data.get("name", city.strip())
    except (KeyError, IndexError, ValueError, TypeError):
        return None

    snapshot = WeatherSnapshot(
        city=resolved_name,
        temp=round(temp, 1),
        condition=condition_desc,
        bucket=temp_to_bucket(temp, weather_main),
    )
    _cache_set(city_key, snapshot)
    return snapshot
