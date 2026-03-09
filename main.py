"""
OutfitNow — FastAPI веб-панель статистики.
Запуск: uvicorn main:app --reload
Работает параллельно с ботом (bot.py).
"""
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from models.outfit import Outfit
from services import storage

app = FastAPI(title="OutfitNow Stats", version="1.0")

# Загружаем базу образов
DATA_PATH = Path(__file__).resolve().parent / "data" / "outfits.json"
with open(DATA_PATH, encoding="utf-8") as f:
    OUTFITS: list[Outfit] = [Outfit(**o) for o in json.load(f)]


# /health
@app.get("/health", tags=["System"])
async def health():
    """Проверка работоспособности сервиса."""
    return {"status": "ok", "bot": "OutfitNow"}


# /outfits
@app.get("/outfits", tags=["Data"])
async def get_outfits(gender: str | None = None):
    """
    Список всех образов из базы.
    Параметр ?gender=male или ?gender=female для фильтрации.
    """
    result = OUTFITS
    if gender:
        result = [o for o in OUTFITS if gender in o.gender]
    return {
        "total": len(result),
        "outfits": [o.model_dump() for o in result],
    }


# /stats
@app.get("/stats", tags=["Analytics"])
async def get_stats():
    """Статистика использования бота."""
    saved_data = storage._saved  # noqa: SLF001

    total_users = len(saved_data)
    total_saved = sum(len(v) for v in saved_data.values())

    males = [o for o in OUTFITS if "male" in o.gender]
    females = [o for o in OUTFITS if "female" in o.gender]

    # Топ сохранённых образов
    outfit_counter: dict[str, int] = {}
    for outfits in saved_data.values():
        for outfit in outfits:
            outfit_counter[outfit.name] = outfit_counter.get(outfit.name, 0) + 1
    top_outfits = sorted(outfit_counter.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "users": {
            "total_unique": total_users,
        },
        "saves": {
            "total_saved_outfits": total_saved,
            "avg_saves_per_user": round(total_saved / total_users, 2) if total_users else 0,
        },
        "top_saved_outfits": [{"name": n, "saves": c} for n, c in top_outfits],
        "database": {
            "total_outfits": len(OUTFITS),
            "male_outfits": len(males),
            "female_outfits": len(females),
        },
    }


# / - простая HTML-страница
@app.get("/", response_class=HTMLResponse, tags=["System"])
async def dashboard():
    """Простая веб-страница с метриками."""
    saved_data = storage._saved  # noqa: SLF001
    total_users = len(saved_data)
    total_saved = sum(len(v) for v in saved_data.values())

    outfit_counter: dict[str, int] = {}
    for outfits in saved_data.values():
        for outfit in outfits:
            outfit_counter[outfit.name] = outfit_counter.get(outfit.name, 0) + 1
    top_outfits = sorted(outfit_counter.items(), key=lambda x: x[1], reverse=True)[:5]
    top_rows = "".join(
        f"<tr><td>{i+1}</td><td>{name}</td><td>{count}</td></tr>"
        for i, (name, count) in enumerate(top_outfits)
    ) or "<tr><td colspan='3'>Пока нет данных</td></tr>"

    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>OutfitNow — Dashboard</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; background: #f5f5f5; }}
            h1 {{ color: #333; }} h2 {{ color: #555; margin-top: 30px; }}
            .cards {{ display: flex; gap: 20px; flex-wrap: wrap; margin: 20px 0; }}
            .card {{ background: white; border-radius: 12px; padding: 20px 30px; flex: 1; min-width: 150px;
                     box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center; }}
            .card .num {{ font-size: 2.5em; font-weight: bold; color: #6c63ff; }}
            .card .label {{ color: #888; font-size: 0.9em; margin-top: 5px; }}
            table {{ width: 100%; border-collapse: collapse; background: white;
                     border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
            th {{ background: #6c63ff; color: white; padding: 12px; text-align: left; }}
            td {{ padding: 10px 12px; border-bottom: 1px solid #eee; }}
            .links {{ margin-top: 30px; }}
            .links a {{ margin-right: 15px; color: #6c63ff; text-decoration: none; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h1>👗 OutfitNow — Dashboard</h1>
        <div class="cards">
            <div class="card"><div class="num">{total_users}</div><div class="label">Уникальных пользователей</div></div>
            <div class="card"><div class="num">{total_saved}</div><div class="label">Образов сохранено</div></div>
            <div class="card"><div class="num">{len(OUTFITS)}</div><div class="label">Образов в базе</div></div>
        </div>
        <h2>🏆 Топ сохранённых образов</h2>
        <table>
            <tr><th>#</th><th>Образ</th><th>Сохранений</th></tr>
            {top_rows}
        </table>
        <div class="links">
            <a href="/docs">📄 API Docs</a>
            <a href="/stats">📊 JSON Stats</a>
            <a href="/outfits">👕 All Outfits</a>
            <a href="/health">✅ Health</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
