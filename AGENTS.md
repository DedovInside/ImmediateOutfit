# ImmediateOutfit — Codex Project Guide

Учебный продуктовый проект (курс «Управление продуктом»): Telegram-бот для быстрого подбора одежды под ситуацию. Основной артефакт защиты — не только код, а связка MVP + метрики + спринты + roadmap + бизнес-модель.

## Стек

- Python 3.12 (venv в `.venv312/`)
- `aiogram` 3.x — Telegram-бот
- `pydantic` / `pydantic-settings` — модели и конфиг
- `SQLite` через `sqlite3` — единственное хранилище (in-memory не возвращать)
- `FastAPI` + `uvicorn` — продуктовый dashboard
- Recommender — rule-based; DeepSeek API — опциональный AI-слой для текстового разбора образа и нормализации вещи-якоря.

## Точки входа

- [bot.py](bot.py) — Telegram-бот, регистрирует роутеры из `handlers/` и инициализирует SQLite.
- [main.py](main.py) — FastAPI dashboard со страницами `/`, `/stats`, `/outfits`, `/artifacts/{name}`.
- [config.py](config.py) — `BOT_TOKEN`, опциональный `OWM_API_KEY`, опциональные `AI_ENABLED`/`DEEPSEEK_API_KEY`, `DB_PATH` через `.env`.

## Карта кода

- [services/storage.py](services/storage.py) — SQLite-слой (users, profiles, saved_outfits, events) + `get_metrics()`.
- [services/recommender.py](services/recommender.py) — rule-based подбор (`recommend`) и разбор образа (`review_user_outfit`).
- [services/ai_assistant.py](services/ai_assistant.py) — optional DeepSeek API client; при ошибке возвращает `None`, чтобы сработал rule-based fallback.
- [services/catalog.py](services/catalog.py) — мерджит базовые образы, curated overlay и командный каталог через `lru_cache`.
- [handlers/](handlers/) — `start`, `questionnaire`, `results`, `profile`, `premium`.
- [models/states.py](models/states.py) — FSM-состояния анкеты.
- [keyboards/inline.py](keyboards/inline.py) — inline-клавиатуры.
- [data/outfits.json](data/outfits.json) — 40 базовых образов.
- [data/curation.json](data/curation.json) — curated overlay по базовым образам.
- [data/team_outfits.json](data/team_outfits.json) — 82 командные подборки из интервью/ручной стилизации с палитрами и артикулами.
- [ГОТОВЫЕ ОБРАЗЫ С КАРТИНКАМИ.txt](ГОТОВЫЕ%20ОБРАЗЫ%20С%20КАРТИНКАМИ.txt) — исходный текстовый артефакт команды, из которого собран `team_outfits.json`.
- [docs/](docs/) — `metrics.md`, `sprint_map.md`, `roadmap.md`, `unit_economics.md` (учебные артефакты, отдаются через `/artifacts/{name}`).

## Запуск

```bash
source .venv312/bin/activate
python bot.py                    # Telegram-бот (нужен BOT_TOKEN в .env)
uvicorn main:app --reload        # Dashboard на http://127.0.0.1:8000
```

## Тесты

```bash
source .venv312/bin/activate
python test_recommender.py                 # script-style smoke
python -m unittest discover -s tests       # unittest (test_recommender, test_storage)
```

Два файла `test_recommender.py` (в корне и в `tests/`) — это разные форматы (скрипт vs unittest), а не дубликат.

## Продуктовые сценарии (через `/start` → меню)

1. `Подобрать образ` — основной flow через анкету, включая вайб/настроение образа.
2. `Быстрый подбор` — для пользователей с заполненным профилем.
3. `Подобрать под мою вещь` — AI-first свободный текст вокруг item_anchor; при выключенном DeepSeek fallback на кнопочную анкету.
4. `Проверить мой образ` — структурированный разбор текстового описания; при включённом DeepSeek ответ генерируется AI, иначе rule-based.
5. `Premium` — заглушка для сбора интереса.
6. `Мой профиль` / `Мои сохранённые` — управление состоянием.

## Учебные требования курса (как закрыты)

- MVP — есть, расширенный bot-first.
- **11+ метрик** — закрыто 16 в [docs/metrics.md](docs/metrics.md), реально считаются в `services/storage.py:get_metrics()`.
- **6+ спринтов** — описано 7 в [docs/sprint_map.md](docs/sprint_map.md).
- Roadmap — [docs/roadmap.md](docs/roadmap.md).
- Бизнес-модель — [docs/unit_economics.md](docs/unit_economics.md) (freemium гипотеза).
- Отчёт/презентация — пока не в репо.

## Зафиксированные продуктовые решения (не ломать без отдельного обсуждения)

- Основной интерфейс — Telegram-бот. Mini app **отложен**.
- AI try-on / photo-review по изображению — **не входят** в ближайший контур.
- DeepSeek text-AI включается только через `.env`; fallback на rule-based обязателен.
- SQLite — единственное хранилище. **In-memory не возвращать.**
- Не превращать продукт в каталог покупок: интервью подтверждали полезность подбора, а не витрину.

## Известные ограничения и долги

- **Визуальные картинки пока не приложены:** командный каталог содержит референсы текстом, палитры и артикулы; реальные `image_url` можно добавить позже, если команда передаст файлы или ссылки.
- **Авто-погода опциональна:** при наличии `OWM_API_KEY` бот получает погоду через OpenWeatherMap; без ключа остаётся ручной fallback.
- **DeepSeek опционален:** при наличии `AI_ENABLED=true` и `DEEPSEEK_API_KEY` бот использует AI для текстового review и подбора вокруг вещи; без ключа работает локальная fallback-логика.
- **Мало свободного места на машине** — это уже мешало установке. Не плодить большие директории/артефакты.
- В корне присутствуют `.venv` и `.venv312` (используется `.venv312`).
- Реальных пользовательских данных в SQLite пока нет — метрики на дашборде будут пустыми до полевых тестов.

## Приоритеты следующих сессий (из handoff)

1. Поднять окружение, прогнать e2e QA, починить runtime-баги.
2. Довести реальные картинки/ссылки к командным образам, если команда передаст материалы.
3. Усилить работу с цветом, вайбом и несколькими делами в день.
4. Проверить OWM-интеграцию в live QA с реальным ключом.
5. Собирать живые данные метрик в полевых тестах.

## Стиль работы для агента

- Это учебный проект — изменения должны облегчать защиту: ясные артефакты, читаемые метрики, понятный демо-flow.
- Не вводить тяжёлые зависимости без необходимости (диск ограничен).
- Перед изменениями `services/storage.py` помнить, что схема БД уже создана — миграции делать аккуратно.
- Перед изменениями `models/outfit.py` — это контракт для `data/outfits.json` И `data/curation.json` сразу.
