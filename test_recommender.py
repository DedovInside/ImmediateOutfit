"""Быстрый тест recommender engine."""
import json
from services.recommender import recommend, check_user_outfit
from models.outfit import Outfit

outfits = [Outfit(**o) for o in json.load(open("data/outfits.json", encoding="utf-8"))]
males = [o for o in outfits if "male" in o.gender]
females = [o for o in outfits if "female" in o.gender]
print(f"Загружено образов: {len(outfits)} (мужских: {len(males)}, женских: {len(females)})")

# Тест 1: парень, учёба, спокойный день, комфорт, casual
r1 = recommend(
    {"gender": "male", "occasion": "study_work", "activity": "calm", "priority": "comfort", "style": "casual"},
    outfits,
)
print(f"\nТест 1 (ПАРЕНЬ / учёба/спокойный/комфорт/casual): найдено {len(r1)}")
for o in r1:
    print(f"  [{o.id}] {o.name} | gender={o.gender}")
assert all("male" in o.gender for o in r1), "❌ Попался женский образ!"

# Тест 2: девушка, свидание, спокойный, эффектно, минимализм
r2 = recommend(
    {"gender": "female", "occasion": "date", "activity": "calm", "priority": "impressive", "style": "base_minimal"},
    outfits,
)
print(f"\nТест 2 (ДЕВУШКА / свидание/спокойный/эффектно/минимализм): найдено {len(r2)}")
for o in r2:
    print(f"  [{o.id}] {o.name} | gender={o.gender}")
assert all("female" in o.gender for o in r2), "❌ Попался мужской образ!"

# Тест 3: парень, мероприятие, активный, баланс, спортивный
r3 = recommend(
    {"gender": "male", "occasion": "event", "activity": "active", "priority": "balance", "style": "sport"},
    outfits,
)
print(f"\nТест 3 (ПАРЕНЬ / мероприятие/активный/баланс/спортивный): найдено {len(r3)}")
for o in r3:
    print(f"  [{o.id}] {o.name} | gender={o.gender}")
assert all("male" in o.gender for o in r3), "❌ Попался женский образ!"

# Тест 4: «Показать ещё» - исключаем уже показанные
shown = [o.id for o in r1]
r4 = recommend(
    {"gender": "male", "occasion": "study_work", "activity": "calm", "priority": "comfort", "style": "casual"},
    outfits,
    shown_ids=shown,
)
print(f"\nТест 4 (показать ещё, исключая {shown}): найдено {len(r4)}")
for o in r4:
    print(f"  [{o.id}] {o.name}")
assert not any(o.id in shown for o in r4), "❌ Вернулся уже показанный образ!"

# Тест 5: проверка образа
result = check_user_outfit("водолазка, джинсы, кроссовки", outfits)
print(f"\nТест 5 (проверить образ 'водолазка, джинсы, кроссовки'):")
print(f"  {result[:100]}...")

print("\n✅ Все тесты пройдены!")

