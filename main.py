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
ALLOWED_ARTIFACTS = {"metrics", "sprint_map", "roadmap", "unit_economics", "qa_checklist", "mvp_scope"}


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
  body {{ font-family: Inter, Arial, sans-serif; max-width: 900px; margin: 32px auto; padding: 0 18px 48px;
         background: radial-gradient(circle at 80% 0%, rgba(196,92,255,.32), transparent 34%),
                     radial-gradient(circle at 12% 18%, rgba(255,115,210,.22), transparent 30%),
                     #0c0814; color: #f7f1ff; line-height: 1.58; }}
  h1, h2, h3 {{ color: #ffffff; margin-top: 1.4em; }}
  h1 {{ border-bottom: 1px solid #332343; padding-bottom: 8px; }}
  code {{ background: #1c1428; color: #ffd8f5; padding: 2px 6px; border-radius: 4px; font-size: 0.92em; }}
  ul {{ padding-left: 22px; }}
  li {{ margin: 4px 0; }}
  a.back {{ display: inline-block; margin-bottom: 16px; color: #ff73d2; text-decoration: none; font-weight: bold; }}
  p, li {{ color: #d8cfe4; }}
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
    "mood": "Вайб",
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
    aarrr = metrics["aarrr"]
    aarrr_events = metrics["aarrr_events"]
    funnel = metrics["funnel"]
    engagement = metrics["engagement"]
    quality = metrics["quality"]
    users = metrics["users"]
    quiz_started = funnel["quiz_started"] or 0
    has_data = quiz_started > 0

    cards = [
        ("Новые пользователи", aarrr_events["new_users"], None),
        ("CAC", f"{aarrr_events['cac']} ₽" if aarrr_events["cac"] else "—", aarrr_events["cac"] > 0),
        ("Activation", _percent(aarrr_events["scenario_completion_rate"]), users["total_unique"] > 0),
        ("AI stylist share", _percent(aarrr_events["ai_stylist_share"]), users["total_unique"] > 0),
        ("Premium interest", _percent(quality["premium_interest_rate"]), users["total_unique"] > 0),
        ("AI ответы", engagement["ai_quota_used_total"], True),
    ]
    cards_html = "".join(
        f"<div class='card'><div class='num'>{value if (active is None or active) else '—'}</div>"
        f"<div class='label'>{escape(label)}</div></div>"
        for label, value, active in cards
    )
    aarrr_rows = [
        ("Новые пользователи", aarrr_events["new_users"]),
        ("Среднее время до результата", f"{aarrr_events['avg_time_to_result_min']} мин"),
        ("Конверсия в завершение сценария", _percent(aarrr_events["scenario_completion_rate"])),
        ("Среднее количество сценариев", aarrr_events["avg_scenarios"]),
        ("Retention D1", _percent(aarrr_events["retention_d1"])),
        ("Retention D7", _percent(aarrr_events["retention_d7"])),
        ("Retention D30", _percent(aarrr_events["retention_d30"])),
        ("Доля пользователей ИИ-стилиста", _percent(aarrr_events["ai_stylist_share"])),
        ("Средняя длина сессии", f"{aarrr_events['avg_session_length_min']} мин"),
        ("Среднее кол-во обращений", aarrr_events["avg_bot_requests"]),
        ("Частота использования ИИ", aarrr_events["ai_usage_frequency"]),
        ("CAC", f"{aarrr_events['cac']} ₽"),
    ]
    aarrr_html = "".join(
        f"<tr><td>{escape(str(label))}</td><td>{value}</td></tr>"
        for label, value in aarrr_rows
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
                --bg: #0c0814;
                --panel: rgba(24, 18, 34, 0.88);
                --card: rgba(31, 23, 45, 0.94);
                --card-strong: #241832;
                --accent: #c45cff;
                --accent-2: #ff73d2;
                --cyan: #78e2ff;
                --text: #f7f1ff;
                --muted: #b8aec7;
                --border: rgba(255, 255, 255, 0.12);
            }}
            body {{
                font-family: Inter, Arial, sans-serif;
                max-width: 1180px;
                margin: 0 auto;
                padding: 36px 18px 56px;
                background:
                    radial-gradient(circle at 85% 0%, rgba(196, 92, 255, 0.34), transparent 32%),
                    radial-gradient(circle at 10% 12%, rgba(255, 115, 210, 0.24), transparent 28%),
                    linear-gradient(135deg, #0c0814 0%, #130d1e 48%, #20112b 100%);
                color: var(--text);
            }}
            h1, h2, h3 {{ color: #ffffff; letter-spacing: 0; }}
            h1 {{ font-size: 2.35rem; margin-bottom: 8px; }}
            p {{ color: var(--muted); }}
            .hero {{
                display: grid;
                grid-template-columns: 1.4fr 0.8fr;
                gap: 18px;
                align-items: stretch;
                margin-bottom: 22px;
            }}
            .hero-panel {{
                background: linear-gradient(135deg, rgba(196,92,255,.26), rgba(255,115,210,.12)), var(--panel);
                border: 1px solid var(--border);
                border-radius: 24px;
                padding: 26px;
                box-shadow: 0 22px 70px rgba(0,0,0,.28);
            }}
            .pill {{
                display: inline-flex;
                gap: 8px;
                align-items: center;
                padding: 7px 11px;
                border: 1px solid rgba(255,255,255,.16);
                border-radius: 999px;
                color: #ffd8f5;
                background: rgba(255,255,255,.06);
                font-size: .9rem;
            }}
            .cards {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 16px;
                margin: 24px 0;
            }}
            .card {{
                background: var(--card);
                border: 1px solid var(--border);
                border-radius: 14px;
                padding: 18px;
                box-shadow: 0 18px 48px rgba(0, 0, 0, 0.18);
            }}
            .num {{ font-size: 2.05rem; font-weight: 800; color: #ffffff; }}
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
                border-radius: 14px;
                overflow: hidden;
                border: 1px solid var(--border);
            }}
            th {{
                background: linear-gradient(90deg, rgba(196,92,255,.42), rgba(255,115,210,.22));
                color: white;
                text-align: left;
                padding: 12px;
            }}
            td {{
                border-bottom: 1px solid var(--border);
                padding: 10px 12px;
            }}
            .note {{
                background: rgba(255,255,255,0.06);
                border-left: 4px solid var(--accent-2);
                padding: 12px 14px;
                border-radius: 12px;
                margin-top: 12px;
            }}
            .links a {{
                color: #ffd8f5;
                text-decoration: none;
                margin-right: 14px;
                font-weight: bold;
            }}
            .muted {{ color: var(--muted); font-size: 0.92em; }}
            .empty {{
                color: var(--muted);
                background: rgba(255,255,255,0.06);
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
                background: rgba(255,255,255,.12);
                height: 18px;
                border-radius: 9px;
                overflow: hidden;
            }}
            .bar-fill {{
                height: 100%;
                background: linear-gradient(90deg, var(--accent), var(--accent-2));
                transition: width 0.4s ease;
            }}
            .bar-value {{ text-align: right; }}
            .bar-fill.fill-pos {{ background: linear-gradient(90deg, #78e2ff, #72ffb6); }}
            .bar-fill.fill-neu {{ background: linear-gradient(90deg, #ffe082, #ffb86c); }}
            .bar-fill.fill-neg {{ background: linear-gradient(90deg, #ff73d2, #ff5c7a); }}
            .comment-item {{
                background: var(--card);
                border-left: 3px solid var(--accent-2);
                border-radius: 8px;
                padding: 8px 12px;
                margin: 6px 0;
                font-size: 0.95em;
            }}
            .section {{
                background: var(--panel);
                border: 1px solid var(--border);
                border-radius: 18px;
                padding: 18px;
                margin-top: 20px;
            }}
            .table-wrap {{ overflow-x: auto; }}
            @media (max-width: 760px) {{
                .hero {{ grid-template-columns: 1fr; }}
                .bar-row {{ grid-template-columns: 1fr; gap: 6px; }}
                .bar-value {{ text-align: left; }}
            }}
        </style>
    </head>
    <body>
        <div class="hero">
            <div class="hero-panel">
                <span class="pill">ImmediateOutfit / AARRR dashboard</span>
                <h1>Product Dashboard</h1>
                <p>Панель продукта: ключевые AARRR-метрики, события бота, воронка, качество рекомендаций и интерес к Premium.</p>
            </div>
            <div class="hero-panel">
                <span class="pill">Аналитика</span>
                <h2>{'Данные готовы' if aarrr["has_dataset"] else 'Данных пока нет'}</h2>
                <p>Маркетинговый расход: <b>{aarrr["marketing_spend"]} ₽</b><br>
                CAC: <b>{aarrr["cac"]} ₽</b><br>
                Live users в SQLite: <b>{users["total_unique"]}</b></p>
            </div>
        </div>

        <div class="cards">{cards_html}</div>

        <div class="section">
            <h2>AARRR-метрики</h2>
                <p>Основные показатели продукта, рассчитанные по событиям в SQLite.</p>
            <div class="table-wrap">
                <table>
                    <tr><th>Метрика</th><th>Данные по событиям</th></tr>
                    {aarrr_html}
                </table>
            </div>
        </div>

        <div class="grid section">
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
                    Outfit check usage: <b>{_value_or_dash(_percent(engagement["outfit_check_usage_rate"]) if users["total_unique"] else None)}</b><br>
                    Premium interest: <b>{_value_or_dash(_percent(quality["premium_interest_rate"]) if users["total_unique"] else None)}</b><br>
                    AI free limit used: <b>{engagement["ai_quota_used_total"]}</b>
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
            <a href="/artifacts/mvp_scope">MVP Scope</a>
            <a href="/outfits">Outfits Catalog</a>
            <a href="/docs">API Docs</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
