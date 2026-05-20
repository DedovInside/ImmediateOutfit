"""
FastAPI-панель статистики и артефактов по продукту.
Запуск: uvicorn main:app --reload
"""
import re
from contextlib import asynccontextmanager
from html import escape
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from services import storage
from services.catalog import get_outfits


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage.init_db()
    yield


app = FastAPI(title="ImmediateOutfit Stats", version="2.0", lifespan=lifespan)
DOCS_DIR = (Path(__file__).resolve().parent / "docs").resolve()
ALLOWED_ARTIFACTS = {"metrics", "sprint_map", "roadmap", "unit_economics", "qa_checklist"}


def _percent(value: float) -> str:
    return f"{round(value * 100, 1)}%"


def _inline_md(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


def _markdown_to_html(source: str) -> str:
    out: list[str] = []
    in_list = False
    for raw in source.splitlines():
        line = escape(raw).rstrip()
        if line.startswith("### "):
            if in_list:
                out.append("</ul>"); in_list = False
            out.append(f"<h3>{_inline_md(line[4:])}</h3>")
        elif line.startswith("## "):
            if in_list:
                out.append("</ul>"); in_list = False
            out.append(f"<h2>{_inline_md(line[3:])}</h2>")
        elif line.startswith("# "):
            if in_list:
                out.append("</ul>"); in_list = False
            out.append(f"<h1>{_inline_md(line[2:])}</h1>")
        elif re.match(r"^[-*] ", line):
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append(f"<li>{_inline_md(line[2:])}</li>")
        elif not line:
            if in_list:
                out.append("</ul>"); in_list = False
        else:
            if in_list:
                out.append("</ul>"); in_list = False
            out.append(f"<p>{_inline_md(line)}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


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
    if name not in ALLOWED_ARTIFACTS:
        return HTMLResponse("<h1>Artifact not found</h1>", status_code=404)
    path = DOCS_DIR / f"{name}.md"
    if not path.exists():
        return HTMLResponse("<h1>Artifact not found</h1>", status_code=404)
    body = _markdown_to_html(path.read_text(encoding="utf-8"))
    page = f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(name)} — ImmediateOutfit</title>
<style>
  body {{ font-family: Georgia, serif; max-width: 860px; margin: 32px auto; padding: 0 18px 48px;
         background: #f4efe8; color: #2b2521; line-height: 1.55; }}
  h1, h2, h3 {{ color: #6f3d28; margin-top: 1.4em; }}
  h1 {{ border-bottom: 2px solid #eadfd4; padding-bottom: 8px; }}
  code {{ background: #fffaf3; padding: 2px 6px; border-radius: 4px; font-size: 0.92em; }}
  ul {{ padding-left: 22px; }}
  li {{ margin: 4px 0; }}
  a.back {{ display: inline-block; margin-bottom: 16px; color: #ae5f3d; text-decoration: none; font-weight: bold; }}
</style></head><body>
<a class="back" href="/">⬅ К дашборду</a>
{body}
</body></html>"""
    return HTMLResponse(page)


STEP_LABELS = {
    "gender": "Пол",
    "occasion": "Куда идёшь",
    "weather": "Погода",
    "activity": "Активность",
    "priority": "Приоритет",
    "budget": "Бюджет",
    "style": "Стиль",
}
STEP_ORDER = list(STEP_LABELS.keys())


def _value_or_dash(value, suffix: str = "") -> str:
    if not value:
        return "<span class='muted'>нет данных</span>"
    return f"{value}{suffix}"


@app.get("/", response_class=HTMLResponse, tags=["System"])
async def dashboard():
    metrics = storage.get_metrics()
    funnel = metrics["funnel"]
    engagement = metrics["engagement"]
    quality = metrics["quality"]
    users = metrics["users"]
    quiz_started = funnel["quiz_started"] or 0
    has_data = quiz_started > 0

    cards = [
        ("Пользователи", users["total_unique"], None),
        ("Стартов анкеты", quiz_started, None),
        ("Completion rate", _percent(funnel["quiz_completion_rate"]), has_data),
        ("Save rate", _percent(engagement["save_rate"]), engagement["saved_outfits_total"] > 0),
        ("Repeat usage", _percent(engagement["repeat_usage_rate"]), users["total_unique"] > 0),
        ("Premium interest", _percent(quality["premium_interest_rate"]), users["total_unique"] > 0),
    ]
    cards_html = "".join(
        f"<div class='card'><div class='num'>{value if (active is None or active) else '—'}</div>"
        f"<div class='label'>{escape(label)}</div></div>"
        for label, value, active in cards
    )

    dropoff = funnel["dropoff_by_step"]
    max_count = max([quiz_started, *dropoff.values()] or [1])
    funnel_rows = []
    for step in STEP_ORDER:
        count = dropoff.get(step, 0)
        pct = round((count / max_count) * 100, 1) if max_count else 0
        share = f"{pct}%" if has_data else "—"
        funnel_rows.append(
            f"<div class='bar-row'>"
            f"<div class='bar-label'>{escape(STEP_LABELS[step])}</div>"
            f"<div class='bar-track'><div class='bar-fill' style='width:{pct}%'></div></div>"
            f"<div class='bar-value'>{count} <span class='muted'>({share})</span></div>"
            f"</div>"
        )
    funnel_html = "".join(funnel_rows) if has_data else (
        "<div class='empty'>Воронка появится после первых прохождений анкеты.</div>"
        + "".join(funnel_rows)
    )

    event_rows = "".join(
        f"<tr><td>{escape(name)}</td><td>{count}</td></tr>"
        for name, count in sorted(metrics["events"].items(), key=lambda item: item[1], reverse=True)[:12]
    ) or "<tr><td colspan='2' class='muted'>Пока нет событий</td></tr>"

    def _distribution_bars(dist: dict[str, int]) -> str:
        total = dist["positive"] + dist["neutral"] + dist["negative"]
        if not total:
            return "<div class='empty'>Оценки появятся после первых ответов пользователей.</div>"
        labels = [
            ("👍 Полезно", "positive", "fill-pos"),
            ("🤔 Норм", "neutral", "fill-neu"),
            ("👎 Мимо", "negative", "fill-neg"),
        ]
        rows = []
        for label, key, css in labels:
            count = dist[key]
            pct = round(count / total * 100, 1) if total else 0
            rows.append(
                f"<div class='bar-row'>"
                f"<div class='bar-label'>{label}</div>"
                f"<div class='bar-track'><div class='bar-fill {css}' style='width:{pct}%'></div></div>"
                f"<div class='bar-value'>{count} <span class='muted'>({pct}%)</span></div>"
                f"</div>"
            )
        return "".join(rows)

    result_dist_html = _distribution_bars(quality["result_feedback_distribution"])
    review_dist_html = _distribution_bars(quality["review_feedback_distribution"])

    def _comments_block(comments: list[dict]) -> str:
        if not comments:
            return "<div class='empty muted'>Пока нет текстовых комментариев.</div>"
        items = []
        for c in comments:
            score_emoji = {5: "👍", 3: "🤔", 1: "👎"}.get(c.get("score"), "•")
            items.append(
                f"<div class='comment-item'>{score_emoji} <i>«{escape(c['text'])}»</i></div>"
            )
        return "".join(items)

    result_comments_html = _comments_block(quality["recent_feedback_comments"]["result"])
    review_comments_html = _comments_block(quality["recent_feedback_comments"]["review"])

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
            .muted {{ color: var(--muted); font-size: 0.92em; }}
            .empty {{
                color: var(--muted);
                background: rgba(255,255,255,0.5);
                border-radius: 12px;
                padding: 10px 14px;
                margin-bottom: 12px;
                font-style: italic;
            }}
            .bar-row {{
                display: grid;
                grid-template-columns: 130px 1fr 110px;
                gap: 12px;
                align-items: center;
                margin: 8px 0;
            }}
            .bar-label {{ color: var(--text); font-weight: bold; }}
            .bar-track {{
                background: var(--border);
                height: 18px;
                border-radius: 9px;
                overflow: hidden;
            }}
            .bar-fill {{
                height: 100%;
                background: linear-gradient(90deg, var(--accent), var(--accent-dark));
                transition: width 0.4s ease;
            }}
            .bar-value {{ text-align: right; }}
            .bar-fill.fill-pos {{ background: linear-gradient(90deg, #6fb27a, #3d8c54); }}
            .bar-fill.fill-neu {{ background: linear-gradient(90deg, #d4b16a, #a37b35); }}
            .bar-fill.fill-neg {{ background: linear-gradient(90deg, #d77676, #a23b3b); }}
            .comment-item {{
                background: var(--card);
                border-left: 3px solid var(--accent);
                border-radius: 8px;
                padding: 8px 12px;
                margin: 6px 0;
                font-size: 0.95em;
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
                {funnel_html}
                <div class="note">
                    Result view rate: <b>{_value_or_dash(_percent(funnel["result_view_rate"]) if has_data else None)}</b><br>
                    Profile completion: <b>{_value_or_dash(_percent(engagement["profile_completion_rate"]) if users["total_unique"] else None)}</b><br>
                    Weather usage: <b>{_value_or_dash(_percent(engagement["weather_usage_rate"]) if has_data else None)}</b>
                </div>
            </div>
            <div>
                <h2>Ключевые события</h2>
                <table>
                    <tr><th>Событие</th><th>Количество</th></tr>
                    {event_rows}
                </table>
                <div class="note">
                    Satisfaction rate: <b>{_value_or_dash(quality["satisfaction_rate"] or None)}</b><br>
                    Review satisfaction: <b>{_value_or_dash(quality["review_satisfaction_rate"] or None)}</b><br>
                    Outfit check usage: <b>{_value_or_dash(_percent(engagement["outfit_check_usage_rate"]) if users["total_unique"] else None)}</b>
                </div>
            </div>
        </div>

        <h2>Голоса и комментарии</h2>
        <div class="grid">
            <div>
                <h3>Оценки результата подбора</h3>
                {result_dist_html}
                <h3 style="margin-top: 18px;">Последние комментарии</h3>
                {result_comments_html}
            </div>
            <div>
                <h3>Оценки разбора образа</h3>
                {review_dist_html}
                <h3 style="margin-top: 18px;">Последние комментарии</h3>
                {review_comments_html}
            </div>
        </div>

        <h2>Артефакты курса</h2>
        <div class="links">
            <a href="/stats">JSON Stats</a>
            <a href="/artifacts/metrics">Metrics</a>
            <a href="/artifacts/sprint_map">Sprint Map</a>
            <a href="/artifacts/roadmap">Roadmap</a>
            <a href="/artifacts/unit_economics">Unit Economics</a>
            <a href="/artifacts/qa_checklist">QA Checklist</a>
            <a href="/outfits">Outfits Catalog</a>
            <a href="/docs">API Docs</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
