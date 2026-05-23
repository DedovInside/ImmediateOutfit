"""
Опциональный AI-слой поверх rule-based MVP.

DeepSeek используется только если явно включён в .env. При любой ошибке
функции возвращают None, а хендлеры падают обратно на локальную логику.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from config import settings
from models.profile import UserProfile
from services.recommender import ReviewResult

DEEPSEEK_CHAT_PATH = "/chat/completions"


@dataclass(frozen=True)
class ItemAnchorExpansion:
    normalized_item: str
    search_text: str
    item_type: str | None = None
    colors: list[str] | None = None
    style_hints: list[str] | None = None
    compatible_items: list[str] | None = None


@dataclass(frozen=True)
class ItemOutfitSuggestion:
    title: str
    items: list[str]
    why_it_fits: list[str]
    styling_tips: list[str]
    colors: list[str]
    avoid: list[str]


def is_ai_enabled() -> bool:
    return bool(settings.AI_ENABLED and settings.DEEPSEEK_API_KEY.strip())


def _base_url() -> str:
    return settings.DEEPSEEK_BASE_URL.rstrip("/")


def _safe_str_list(value: Any, limit: int = 4) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            result.append(text[:180])
        if len(result) >= limit:
            break
    return result


def _safe_text(value: Any, fallback: str = "", limit: int = 220) -> str:
    text = str(value or "").strip()
    return (text or fallback)[:limit]


async def _deepseek_json(messages: list[dict[str, str]], max_tokens: int = 700) -> dict[str, Any] | None:
    if not is_ai_enabled():
        return None

    try:
        import aiohttp
    except ImportError:
        return None

    payload: dict[str, Any] = {
        "model": settings.DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": 0.35,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
        "thinking": {"type": "disabled"},
    }
    headers = {
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY.strip()}",
        "Content-Type": "application/json",
    }
    timeout = aiohttp.ClientTimeout(total=max(5, settings.DEEPSEEK_TIMEOUT_SECONDS))

    async def _post(payload_to_send: dict[str, Any]) -> tuple[int, dict[str, Any] | None]:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{_base_url()}{DEEPSEEK_CHAT_PATH}",
                headers=headers,
                json=payload_to_send,
            ) as response:
                if response.status != 200:
                    return response.status, None
                return response.status, await response.json()

    try:
        status, data = await _post(payload)
        if status == 400:
            retry_payload = dict(payload)
            retry_payload.pop("thinking", None)
            status, data = await _post(retry_payload)
        if status != 200 or data is None:
            return None
    except (aiohttp.ClientError, TimeoutError, json.JSONDecodeError):
        return None

    try:
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _profile_context(profile: UserProfile | None) -> str:
    if not profile:
        return "Профиль пользователя не заполнен."
    parts = [
        f"пол: {profile.gender or 'не указан'}",
        f"стиль: {profile.style or 'не указан'}",
        f"бюджет: {profile.budget or 'не указан'}",
    ]
    if profile.preferred_colors:
        parts.append("любимые цвета: " + ", ".join(profile.preferred_colors[:6]))
    if profile.disliked_items:
        parts.append("не любит: " + ", ".join(profile.disliked_items[:6]))
    if profile.key_items:
        parts.append("ключевые вещи: " + ", ".join(profile.key_items[:8]))
    return "; ".join(parts)


async def ai_review_outfit(user_text: str, profile: UserProfile | None = None) -> ReviewResult | None:
    text = user_text.strip()
    if len(text) < 8:
        return None

    system_prompt = (
        "Ты дружелюбный стилист для Telegram-бота ImmediateOutfit. "
        "Оцени описанный пользователем образ на русском языке. "
        "Не выдумывай, что видел фото: у тебя только текст. "
        "Будь конкретным, коротким и практичным. "
        "Верни только JSON без Markdown."
    )
    user_prompt = (
        "Проверь образ пользователя.\n"
        f"Профиль: {_profile_context(profile)}\n"
        f"Описание образа: {text}\n\n"
        "Формат JSON строго такой:\n"
        "{"
        "\"headline\":\"короткий вывод\","
        "\"score_label\":\"например 8/10\","
        "\"strengths\":[\"1-3 пункта что хорошо\"],"
        "\"concerns\":[\"1-3 пункта что спорно\"],"
        "\"suggestions\":[\"1-3 конкретных совета как усилить\"]"
        "}"
    )
    parsed = await _deepseek_json(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=700,
    )
    if not parsed:
        return None

    strengths = _safe_str_list(parsed.get("strengths"), limit=3)
    concerns = _safe_str_list(parsed.get("concerns"), limit=3)
    suggestions = _safe_str_list(parsed.get("suggestions"), limit=3)
    if not any((strengths, concerns, suggestions)):
        return None

    return ReviewResult(
        headline=_safe_text(parsed.get("headline"), "Образ можно чуть усилить."),
        score_label=_safe_text(parsed.get("score_label"), "7/10", limit=40),
        strengths=strengths or ["у образа уже есть понятная идея"],
        concerns=concerns or ["жёстких конфликтов по описанию не вижу"],
        suggestions=suggestions or ["проверь посадку и добавь один аккуратный акцент"],
        needs_more_input=False,
    )


async def ai_expand_item_anchor(user_text: str, profile: UserProfile | None = None) -> ItemAnchorExpansion | None:
    text = user_text.strip()
    if len(text) < 3:
        return None

    system_prompt = (
        "Ты помогаешь Telegram-боту подобрать образ вокруг вещи пользователя. "
        "Нужно нормализовать текст и расширить его словами, по которым rule-based каталог "
        "сможет найти похожие образы. Верни только JSON без Markdown."
    )
    user_prompt = (
        "Разбери вещь-якорь пользователя.\n"
        f"Профиль: {_profile_context(profile)}\n"
        f"Вещь: {text}\n\n"
        "Формат JSON строго такой:\n"
        "{"
        "\"normalized_item\":\"короткое нормальное название вещи\","
        "\"item_type\":\"тип вещи\","
        "\"colors\":[\"цвета если есть\"],"
        "\"style_hints\":[\"base_minimal/casual/sport/classic или русские подсказки\"],"
        "\"compatible_items\":[\"с чем сочетать: джинсы, брюки, кеды...\"],"
        "\"search_text\":\"строка для поиска по каталогу, 8-16 слов\""
        "}"
    )
    parsed = await _deepseek_json(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=450,
    )
    if not parsed:
        return None

    normalized_item = _safe_text(parsed.get("normalized_item"), text, limit=120)
    search_text = _safe_text(parsed.get("search_text"), text, limit=240)
    if not normalized_item or not search_text:
        return None

    return ItemAnchorExpansion(
        normalized_item=normalized_item,
        search_text=search_text,
        item_type=_safe_text(parsed.get("item_type"), "", limit=80) or None,
        colors=_safe_str_list(parsed.get("colors"), limit=4),
        style_hints=_safe_str_list(parsed.get("style_hints"), limit=5),
        compatible_items=_safe_str_list(parsed.get("compatible_items"), limit=8),
    )


async def ai_suggest_outfits_for_item(
    user_text: str,
    profile: UserProfile | None = None,
) -> list[ItemOutfitSuggestion] | None:
    text = user_text.strip()
    if len(text) < 3:
        return None

    system_prompt = (
        "Ты дружелюбный стилист Telegram-бота ImmediateOutfit. "
        "Пользователь описывает вещь, вокруг которой хочет собрать образ, "
        "и может сразу добавить погоду, событие, активность, настроение или ограничения. "
        "Собери 2-3 применимых варианта образа на русском языке. "
        "Не выдумывай конкретные артикулы и ссылки. Если нужна покупка, называй только категорию вещи. "
        "Пиши коротко, конкретно и носибельно. Верни только JSON без Markdown."
    )
    user_prompt = (
        "Собери варианты образа вокруг вещи пользователя.\n"
        f"Профиль: {_profile_context(profile)}\n"
        f"Запрос пользователя: {text}\n\n"
        "Учти, если пользователь сам указал погоду, событие, стиль, активность или настроение. "
        "Если деталей мало, дай универсальные варианты и не задавай уточняющих вопросов.\n\n"
        "Формат JSON строго такой:\n"
        "{"
        "\"variants\":["
        "{"
        "\"title\":\"короткое название варианта\","
        "\"items\":[\"верх\", \"низ\", \"обувь\", \"слой/аксессуар если нужен\"],"
        "\"why_it_fits\":[\"1-3 причины\"],"
        "\"styling_tips\":[\"1-3 совета по носке\"],"
        "\"colors\":[\"подходящие цвета/палитра\"],"
        "\"avoid\":[\"чего лучше избегать\"]"
        "}"
        "]"
        "}"
    )
    parsed = await _deepseek_json(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=1000,
    )
    if not parsed or not isinstance(parsed.get("variants"), list):
        return None

    suggestions: list[ItemOutfitSuggestion] = []
    for item in parsed["variants"][:3]:
        if not isinstance(item, dict):
            continue
        title = _safe_text(item.get("title"), "Вариант образа", limit=100)
        outfit_items = _safe_str_list(item.get("items"), limit=6)
        why_it_fits = _safe_str_list(item.get("why_it_fits"), limit=3)
        styling_tips = _safe_str_list(item.get("styling_tips"), limit=3)
        colors = _safe_str_list(item.get("colors"), limit=4)
        avoid = _safe_str_list(item.get("avoid"), limit=3)
        if outfit_items:
            suggestions.append(
                ItemOutfitSuggestion(
                    title=title,
                    items=outfit_items,
                    why_it_fits=why_it_fits or ["собран вокруг вещи из твоего запроса"],
                    styling_tips=styling_tips or ["проверь посадку и оставь один главный акцент"],
                    colors=colors,
                    avoid=avoid,
                )
            )
    return suggestions or None
