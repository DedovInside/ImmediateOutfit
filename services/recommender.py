"""
Rule-based движок подбора образов.
Фильтрует outfits.json по ответам пользователя, ранжирует по релевантности.
"""
from __future__ import annotations

from models.outfit import Outfit


def recommend(
    answers: dict[str, str],
    outfits: list[Outfit],
    shown_ids: list[str] | None = None,
    weather_tag: str | None = None,
    limit: int = 2,
) -> list[Outfit]:
    """
    Подбирает образы под ответы пользователя.

    answers - dict вида:
        {
            "gender": "male" / "female",
            "occasion": "study_work",
            "activity": "calm",
            "priority": "comfort",
            "style": "casual",
        }
    shown_ids - id уже показанных образов (для «Показать ещё»).
    weather_tag - "cold" / "mild" / "warm" / "rain" (опционально).
    limit - максимум образов к выдаче.
    """
    shown_ids = shown_ids or []
    gender = answers.get("gender")  # "male" / "female" / None
    user_occasion = answers.get("occasion")

    scored: list[tuple[int, Outfit]] = []
    for outfit in outfits:
        if outfit.id in shown_ids:
            continue

        # Фильтр по полу: пропускаем если пол не совпадает
        if gender and gender not in outfit.gender:
            continue

        # Жёсткий фильтр по occasion: образ обязан подходить под ситуацию пользователя
        if user_occasion and user_occasion not in outfit.occasion:
            continue

        # Блокируем дождевые образы, если погода явно не "rain"
        if outfit.weather == ["rain"] and weather_tag != "rain":
            continue

        score = 0
        # Три оси (occasion уже проверен выше как жёсткий фильтр)
        if answers.get("activity") in outfit.activity:
            score += 3
        if answers.get("priority") in outfit.priority:
            score += 3
        if answers.get("style") in outfit.style:
            score += 2

        # Бонус за погоду
        if weather_tag and weather_tag in outfit.weather:
            score += 1

        # Минимальный порог: хотя бы один параметр из трёх совпал
        if score >= 2:
            scored.append((score, outfit))

    # Сортируем по убыванию score
    scored.sort(key=lambda x: x[0], reverse=True)

    results = [outfit for _, outfit in scored[:limit]]

    # Если ничего не нашли — вернём образы с нужным occasion для нужного пола
    if not results:
        fallback = [
            o for o in outfits
            if o.id not in shown_ids
            and (not gender or gender in o.gender)
            and (not user_occasion or user_occasion in o.occasion)
            and not (o.weather == ["rain"] and weather_tag != "rain")
        ]
        fallback.sort(
            key=lambda o: (
                (1 if answers.get("activity") in o.activity else 0)
                + (1 if answers.get("priority") in o.priority else 0)
                + (1 if answers.get("style") in o.style else 0)
            ),
            reverse=True,
        )
        results = fallback[:limit]

    return results


def check_user_outfit(user_text: str, outfits: list[Outfit]) -> str:
    """
    Простой keyword-matching: пользователь описывает свой образ текстом,
    бот ищет пересечения с известными образами и даёт оценку.
    """
    text_lower = user_text.lower()

    # Собираем ключевые слова из всех items
    best_match: Outfit | None = None
    best_score = 0
    for outfit in outfits:
        score = 0
        for item_text in outfit.items.values():
            words = item_text.lower().split()
            for word in words:
                clean = word.strip("(),./!?")
                if len(clean) > 3 and clean in text_lower:
                    score += 1
        if score > best_score:
            best_score = score
            best_match = outfit

    if best_match and best_score >= 2:
        return (
            f"Похоже, твой образ ближе всего к стилю «{best_match.name}» 👌\n\n"
            f"{best_match.description}\n\n"
            f"💡 Совет: {best_match.tip}"
        )
    elif best_match and best_score >= 1:
        return (
            "Звучит неплохо! Я вижу элементы стиля, но могу предложить улучшение:\n\n"
            f"💡 {best_match.tip}\n\n"
            "Хочешь, подберу полный образ под твой день?"
        )
    else:
        return (
            "Интересный выбор! Мне сложно оценить без деталей, "
            "но могу подобрать полный образ под твою ситуацию 😊\n\n"
            "Нажми «Подобрать образ», и я помогу!"
        )

