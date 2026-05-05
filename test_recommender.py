"""Небольшой smoke-test движка рекомендаций."""
from services.catalog import get_outfits
from services.recommender import recommend, review_user_outfit

outfits = get_outfits()
male_results = recommend(
    {
        "gender": "male",
        "occasion": "study_work",
        "weather": "mild",
        "activity": "calm",
        "priority": "comfort",
        "budget": "low",
        "style": "casual",
    },
    outfits,
)
print(f"Найдено мужских образов: {len(male_results)}")
assert male_results, "Не найдено ни одного образа для базового сценария"
assert all("male" in result.outfit.gender for result in male_results)

female_results = recommend(
    {
        "gender": "female",
        "occasion": "date",
        "weather": "mild",
        "activity": "calm",
        "priority": "impressive",
        "budget": "medium",
        "style": "base_minimal",
    },
    outfits,
)
print(f"Найдено женских образов: {len(female_results)}")
assert female_results, "Не найдено ни одного женского образа для сценария свидания"
assert all("female" in result.outfit.gender for result in female_results)

review = review_user_outfit("черная водолазка, голубые джинсы, белые кеды")
print(review.headline)
assert review.strengths, "Разбор образа должен содержать сильные стороны"

print("✅ Smoke-test пройден")
