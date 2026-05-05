"""
FastAPI-панель статистики и артефактов по продукту.
Запуск: uvicorn main:app --reload
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from services import storage
from services.catalog import get_outfits

app = FastAPI(title="ImmediateOutfit Stats", version="2.0")
DOCS_DIR = Path(__file__).resolve().parent / "docs"


def _percent(value: float) -> str:
    return f"{round(value * 100, 1)}%"


@app.on_event("startup")
async def startup() -> None:
    storage.init_db()


@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "product": "ImmediateOutfit"}


@app.get("/outfits", tags=["Data"])
async def get_outfits_route(gender: str | None = None):
    outfits = get_outfits()
    if gender:
        outfits = [outfit for outfit in outfits if gender in outfit.gender]
    return {
        "total": len(outfits),
        "outfits": [outfit.model_dump() for outfit in outfits],
    }


@app.get("/stats", tags=["Analytics"])
async def get_stats():
    return storage.get_metrics()


@app.get("/artifacts/{name}", response_class=HTMLResponse, tags=["Artifacts"])
async def artifact_page(name: str):
    path = DOCS_DIR / f"{name}.md"
    if not path.exists():
        return HTMLResponse("<h1>Artifact not found</h1>", status_code=404)
    content = path.read_text(encoding="utf-8").replace("\n", "<br>")
    return HTMLResponse(f"<html><body style='font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto;'>{content}</body></html>")


@app.get("/", response_class=HTMLResponse, tags=["System"])
async def dashboard():
    metrics = storage.get_metrics()
    funnel = metrics["funnel"]
    engagement = metrics["engagement"]
    quality = metrics["quality"]
    users = metrics["users"]
    cards = {
        "Пользователи": users["total_unique"],
        "Стартов анкеты": funnel["quiz_started"],
        "Completion rate": _percent(funnel["quiz_completion_rate"]),
        "Save rate": _percent(engagement["save_rate"]),
        "Repeat usage": _percent(engagement["repeat_usage_rate"]),
        "Premium interest": _percent(quality["premium_interest_rate"]),
    }
    dropoff_rows = "".join(
        f"<tr><td>{step}</td><td>{count}</td></tr>"
        for step, count in funnel["dropoff_by_step"].items()
    ) or "<tr><td colspan='2'>Пока нет данных</td></tr>"
    event_rows = "".join(
        f"<tr><td>{name}</td><td>{count}</td></tr>"
        for name, count in sorted(metrics["events"].items(), key=lambda item: item[1], reverse=True)[:12]
    ) or "<tr><td colspan='2'>Пока нет данных</td></tr>"

    cards_html = "".join(
        f"<div class='card'><div class='num'>{value}</div><div class='label'>{label}</div></div>"
        for label, value in cards.items()
    )

    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ImmediateOutfit Dashboard</title>
        <style>
            :root {{
                --bg: #f4efe8;
                --card: #fffaf3;
                --accent: #ae5f3d;
                --accent-dark: #6f3d28;
                --text: #2b2521;
                --muted: #76685f;
                --border: #eadfd4;
            }}
            body {{
                font-family: Georgia, serif;
                max-width: 1080px;
                margin: 36px auto;
                padding: 0 18px 48px;
                background: radial-gradient(circle at top right, #efe2d4, var(--bg));
                color: var(--text);
            }}
            h1, h2 {{ color: var(--accent-dark); }}
            .cards {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 16px;
                margin: 24px 0;
            }}
            .card {{
                background: var(--card);
                border: 1px solid var(--border);
                border-radius: 18px;
                padding: 18px;
                box-shadow: 0 10px 30px rgba(111, 61, 40, 0.08);
            }}
            .num {{ font-size: 2.1rem; font-weight: bold; color: var(--accent); }}
            .label {{ color: var(--muted); margin-top: 8px; }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 18px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                background: var(--card);
                border-radius: 16px;
                overflow: hidden;
            }}
            th {{
                background: var(--accent);
                color: white;
                text-align: left;
                padding: 12px;
            }}
            td {{
                border-bottom: 1px solid var(--border);
                padding: 10px 12px;
            }}
            .note {{
                background: rgba(255,255,255,0.6);
                border-left: 4px solid var(--accent);
                padding: 12px 14px;
                border-radius: 12px;
                margin-top: 12px;
            }}
            .links a {{
                color: var(--accent-dark);
                text-decoration: none;
                margin-right: 14px;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <h1>ImmediateOutfit Product Dashboard</h1>
        <p>Панель для продуктовых спринтов: воронка, engagement, quality и артефакты для защиты курса.</p>

        <div class="cards">{cards_html}</div>

        <div class="grid">
            <div>
                <h2>Воронка по шагам</h2>
                <table>
                    <tr><th>Шаг</th><th>Ответов</th></tr>
                    {dropoff_rows}
                </table>
                <div class="note">
                    Result view rate: <b>{_percent(funnel["result_view_rate"])}</b><br>
                    Profile completion: <b>{_percent(engagement["profile_completion_rate"])}</b><br>
                    Weather usage: <b>{_percent(engagement["weather_usage_rate"])}</b>
                </div>
            </div>
            <div>
                <h2>Ключевые события</h2>
                <table>
                    <tr><th>Событие</th><th>Количество</th></tr>
                    {event_rows}
                </table>
                <div class="note">
                    Satisfaction rate: <b>{quality["satisfaction_rate"]}</b><br>
                    Review satisfaction: <b>{quality["review_satisfaction_rate"]}</b><br>
                    Outfit check usage: <b>{_percent(engagement["outfit_check_usage_rate"])}</b>
                </div>
            </div>
        </div>

        <h2>Артефакты курса</h2>
        <div class="links">
            <a href="/stats">JSON Stats</a>
            <a href="/artifacts/metrics">Metrics</a>
            <a href="/artifacts/sprint_map">Sprint Map</a>
            <a href="/artifacts/roadmap">Roadmap</a>
            <a href="/artifacts/unit_economics">Unit Economics</a>
            <a href="/outfits">Outfits Catalog</a>
            <a href="/docs">API Docs</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
