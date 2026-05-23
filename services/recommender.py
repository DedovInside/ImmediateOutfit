"""
Rule-based движок рекомендаций и разбора образа.
"""
from __future__ import annotations

from dataclasses import dataclass

from models.outfit import Outfit
from models.profile import UserProfile

COLOR_WORDS = {
    "черн": "black",
    "бел": "white",
    "сер": "gray",
    "беж": "beige",
    "син": "blue",
    "голуб": "blue",
    "корич": "brown",
    "зелен": "green",
    "крас": "red",
}

SPORT_KEYWORDS = {"кроссовки", "худи", "джоггеры", "спортив", "шорты"}
FORMAL_KEYWORDS = {"пиджак", "рубашка", "лоферы", "челси", "брюки", "пальто", "блейзер"}
TOP_KEYWORDS = {"футболка", "рубашка", "свитер", "водолазка", "лонгслив", "худи", "топ", "кофта"}
BOTTOM_KEYWORDS = {"джинсы", "брюки", "юбка", "карго", "джоггеры", "шорты"}
SHOES_KEYWORDS = {"кеды", "кроссовки", "ботинки", "челси", "лоферы", "дерби", "туфли"}

STYLE_TITLES = {
    "base_minimal": "база / минимализм",
    "casual": "casual",
    "sport": "спорт",
    "classic": "классика",
}

WEATHER_TITLES = {
    "warm": "теплая погода",
    "mild": "переменчивая погода",
    "cold": "холодный день",
    "rain": "дождь",
}

MOOD_TITLES = {
    "neutral": "спокойный и носибельный вайб",
    "cozy": "уютное настроение",
    "bright": "более заметный образ",
    "smart": "собранный вид",
}

BUDGET_ORDER = {"low": 0, "medium": 1, "high": 2}
TEAM_CURATED_SOURCE = "team_curated_txt"


@dataclass
class Recommendation:
    outfit: Outfit
    score: int
    reasons: list[str]


@dataclass
class ReviewResult:
    headline: str
    score_label: str
    strengths: list[str]
    concerns: list[str]
    suggestions: list[str]
    needs_more_input: bool = False


def _keyword_overlap(text: str, haystack: list[str]) -> int:
    text_lower = text.lower()
    return sum(1 for token in haystack if token.lower() in text_lower)


def _item_anchor_score(item_anchor: str | None, outfit: Outfit) -> int:
    if not item_anchor:
        return 0
    outfit_text = " ".join(
        [
            outfit.name,
            outfit.description,
            outfit.tip,
            " ".join(outfit.items.values()),
            " ".join(outfit.palette),
            " ".join(outfit.styling_notes),
        ]
    ).lower()
    anchor_words = [word.strip(" ,.!?") for word in item_anchor.lower().split()]
    return sum(1 for word in anchor_words if len(word) > 2 and word in outfit_text)


def _profile_color_score(profile: UserProfile | None, outfit: Outfit) -> int:
    if not profile or not profile.preferred_colors:
        return 0
    searchable = " ".join(outfit.items.values()).lower()
    return sum(1 for color in profile.preferred_colors if color.lower() in searchable)


def _budget_score(user_budget: str | None, outfit_budget: str) -> int:
    if not user_budget:
        return 0
    left = BUDGET_ORDER.get(user_budget, 1)
    right = BUDGET_ORDER.get(outfit_budget, 1)
    distance = abs(left - right)
    if distance == 0:
        return 2
    if distance == 1:
        return 1
    return -1


def _mood_score(mood: str | None, outfit: Outfit) -> int:
    if not mood:
        return 0
    searchable = " ".join([
        outfit.name,
        outfit.description,
        outfit.tip,
        " ".join(outfit.items.values()),
        " ".join(outfit.palette),
        " ".join(outfit.dress_code),
    ]).lower()
    if mood == "neutral":
        return 2 if any(style in outfit.style for style in ("base_minimal", "casual")) else 0
    if mood == "cozy":
        cozy_tokens = ("свитер", "худи", "кардиган", "мягк", "уют", "тепл", "пальто")
        return 2 if any(token in searchable for token in cozy_tokens) else 0
    if mood == "bright":
        accent_tokens = ("акцент", "ярк", "голуб", "светл", "выраз", "интерес", "аксессуар")
        score = 1 if any(token in searchable for token in accent_tokens) else 0
        return score + (1 if "impressive" in outfit.priority else 0)
    if mood == "smart":
        return 2 if "classic" in outfit.style or any(tag in searchable for tag in ("пиджак", "рубашка", "пальто", "лофер")) else 0
    return 0


def _curation_score(outfit: Outfit) -> int:
    """Командные подборки — основной каталог MVP; старая база остаётся fallback-слоем."""
    return 2 if outfit.source == TEAM_CURATED_SOURCE else 0


def _build_reasons(
    answers: dict[str, str],
    outfit: Outfit,
    profile: UserProfile | None,
    item_anchor: str | None,
) -> list[str]:
    reasons = list(outfit.why_it_fits)
    if answers.get("occasion") and answers["occasion"] in outfit.occasion:
        reasons.append("подходит под формат дня и сценарий, который ты выбрал")
    if answers.get("weather") and answers["weather"] in outfit.weather:
        reasons.append(f"собран под {WEATHER_TITLES.get(answers['weather'], 'погоду дня')}")
    if answers.get("priority") and answers["priority"] in outfit.priority:
        reasons.append("держит тот баланс между удобством и впечатлением, который тебе сейчас важен")
    if answers.get("style") and answers["style"] in outfit.style:
        reasons.append(f"попадает в стиль {STYLE_TITLES.get(answers['style'], answers['style'])}")
    if item_anchor and _item_anchor_score(item_anchor, outfit) > 0:
        reasons.append("учитывает вещь, вокруг которой ты хочешь собрать образ")
    if profile and profile.preferred_colors and _profile_color_score(profile, outfit) > 0:
        reasons.append("поддерживает твои любимые цветовые предпочтения")
    if answers.get("mood") and _mood_score(answers["mood"], outfit) > 0:
        reasons.append(f"попадает в {MOOD_TITLES.get(answers['mood'], 'настроение дня')}")
    # Сохраняем короткость и уникальность объяснений.
    unique_reasons: list[str] = []
    for reason in reasons:
        if reason and reason not in unique_reasons:
            unique_reasons.append(reason)
    return unique_reasons[:4]


def recommend(
    answers: dict[str, str],
    outfits: list[Outfit],
    shown_ids: list[str] | None = None,
    profile: UserProfile | None = None,
    item_anchor: str | None = None,
    limit: int = 2,
) -> list[Recommendation]:
    shown_ids = shown_ids or []
    gender = answers.get("gender") or (profile.gender if profile else None)
    user_occasion = answers.get("occasion")
    weather_tag = answers.get("weather")
    scored: list[Recommendation] = []

    for outfit in outfits:
        if outfit.id in shown_ids:
            continue
        if gender and gender not in outfit.gender:
            continue
        if user_occasion and user_occasion not in outfit.occasion:
            continue
        if weather_tag == "rain" and "rain" not in outfit.weather and "mild" not in outfit.weather:
            continue

        score = 0
        if answers.get("activity") in outfit.activity:
            score += 3
        if answers.get("priority") in outfit.priority:
            score += 3
        if answers.get("style") in outfit.style:
            score += 2
        if weather_tag and weather_tag in outfit.weather:
            score += 2
        if weather_tag and outfit.weather == ["rain"] and weather_tag != "rain":
            score -= 3
        score += _curation_score(outfit)
        score += _mood_score(answers.get("mood"), outfit)
        if answers.get("budget"):
            score += _budget_score(answers["budget"], outfit.budget_level)
        if profile:
            score += _profile_color_score(profile, outfit)
            if profile.preferred_styles and any(style in outfit.style for style in profile.preferred_styles):
                score += 2
            if profile.disliked_items and any(
                disliked.lower() in " ".join(outfit.items.values()).lower()
                for disliked in profile.disliked_items
            ):
                score -= 2
            if profile.key_items:
                score += sum(
                    1 for key_item in profile.key_items
                    if key_item.lower() in " ".join(outfit.items.values()).lower()
                )
        score += min(_item_anchor_score(item_anchor, outfit), 3)

        if score < 2:
            continue

        reasons = _build_reasons(answers, outfit, profile, item_anchor)
        scored.append(Recommendation(outfit=outfit, score=score, reasons=reasons))

    scored.sort(
        key=lambda recommendation: (
            recommendation.score,
            _curation_score(recommendation.outfit),
        ),
        reverse=True,
    )

    if scored:
        return scored[:limit]

    # Fallback: возвращаем просто лучшие по ситуации и погоде.
    fallback: list[Recommendation] = []
    for outfit in outfits:
        if outfit.id in shown_ids:
            continue
        if gender and gender not in outfit.gender:
            continue
        if user_occasion and user_occasion not in outfit.occasion:
            continue
        reasons = _build_reasons(answers, outfit, profile, item_anchor)
        fallback.append(Recommendation(outfit=outfit, score=_curation_score(outfit) or 1, reasons=reasons))
    fallback.sort(
        key=lambda recommendation: (
            recommendation.score,
            _curation_score(recommendation.outfit),
        ),
        reverse=True,
    )
    return fallback[:limit]


def review_user_outfit(user_text: str) -> ReviewResult:
    text = user_text.lower()
    strengths: list[str] = []
    concerns: list[str] = []
    suggestions: list[str] = []

    top_present = any(keyword in text for keyword in TOP_KEYWORDS)
    bottom_present = any(keyword in text for keyword in BOTTOM_KEYWORDS)
    shoes_present = any(keyword in text for keyword in SHOES_KEYWORDS)
    colors_found = {name for token, name in COLOR_WORDS.items() if token in text}
    sport_present = any(keyword in text for keyword in SPORT_KEYWORDS)
    formal_present = any(keyword in text for keyword in FORMAL_KEYWORDS)

    if len(text.strip()) < 8 or not any((top_present, bottom_present, shoes_present, sport_present, formal_present)):
        return ReviewResult(
            headline="Пока не могу нормально проверить образ.",
            score_label="нужно больше деталей",
            strengths=[],
            concerns=[
                "я не увидел в описании конкретных вещей",
            ],
            suggestions=[
                "напиши хотя бы верх, низ и обувь",
                "можно добавить цвет, ситуацию и погоду",
                "пример: черная водолазка, голубые джинсы, белые кеды, иду на учебу",
            ],
            needs_more_input=True,
        )

    if top_present and bottom_present:
        strengths.append("у образа уже есть понятный каркас: верх и низ собраны")
    if shoes_present:
        strengths.append("ты продумал обувь, а она сильно влияет на ощущение цельности образа")
    if len(colors_found) <= 2 and colors_found:
        strengths.append("цветовая палитра выглядит достаточно спокойной и управляемой")

    if not shoes_present:
        concerns.append("по описанию не хватает обуви, а именно она часто собирает образ в финальный вид")
    if not top_present or not bottom_present:
        concerns.append("образ описан слишком общо, поэтому уверенность в сочетании пока средняя")
    if len(colors_found) >= 4:
        concerns.append("цветов слишком много, образ может выглядеть перегруженно")
    if sport_present and formal_present:
        concerns.append("сейчас в луке смешаны спортивные и более формальные элементы, их важно связать общей логикой")

    if sport_present and formal_present:
        suggestions.append("оставь один главный акцент: либо более собранный smart-casual, либо более расслабленный casual")
    if top_present and bottom_present and not shoes_present:
        suggestions.append("добавь обувь в том же уровне формальности, что и верх с низом")
    if len(colors_found) <= 1:
        suggestions.append("можно добавить один акцент через аксессуар или второй оттенок, чтобы образ не казался плоским")
    suggestions.append("проверь посадку и аккуратность вещей: чистая обувь и ровный верх часто дают больше эффекта, чем новая покупка")

    if concerns:
        headline = "Образ выглядит рабочим, но я бы его чуть дособрал."
        score_label = "7/10"
    else:
        headline = "Образ звучит уверенно и уместно."
        score_label = "8.5/10"

    if not strengths:
        strengths.append("видно, что ты уже думаешь про сочетание вещей, а это половина хорошего образа")
    if not concerns:
        concerns.append("жестких конфликтов по описанию не вижу, здесь скорее вопрос вкусовых нюансов")

    return ReviewResult(
        headline=headline,
        score_label=score_label,
        strengths=strengths[:3],
        concerns=concerns[:3],
        suggestions=suggestions[:3],
        needs_more_input=False,
    )
