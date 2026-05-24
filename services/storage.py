"""
SQLite-хранилище пользователей, профилей, сохранений и событий.
"""
from __future__ import annotations

import json
import sqlite3
from collections import Counter
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from config import settings
from models.outfit import Outfit
from models.profile import UserProfile

DB_PATH = Path(settings.DB_PATH)

_connection: sqlite3.Connection | None = None
_connection_path: Path | None = None


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def _get_conn() -> sqlite3.Connection:
    """Возвращает долгоживущее соединение. Пересоздаёт, если сменился DB_PATH (для тестов)."""
    global _connection, _connection_path
    if _connection is None or _connection_path != DB_PATH:
        if _connection is not None:
            _connection.close()
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _connection = sqlite3.connect(DB_PATH, check_same_thread=False)
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA journal_mode=WAL")
        _connection.execute("PRAGMA synchronous=NORMAL")
        _connection_path = DB_PATH
    return _connection


def close_connection() -> None:
    """Закрывает текущее SQLite-соединение. Нужно тестам и аккуратной смене DB_PATH."""
    global _connection, _connection_path
    if _connection is not None:
        _connection.close()
    _connection = None
    _connection_path = None


def init_db() -> None:
    conn = _get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            created_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY,
            gender TEXT,
            style TEXT,
            budget TEXT,
            preferred_colors TEXT NOT NULL DEFAULT '[]',
            preferred_styles TEXT NOT NULL DEFAULT '[]',
            disliked_items TEXT NOT NULL DEFAULT '[]',
            key_items TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS saved_outfits (
            user_id INTEGER NOT NULL,
            outfit_id TEXT NOT NULL,
            outfit_snapshot TEXT NOT NULL,
            saved_at TEXT NOT NULL,
            PRIMARY KEY (user_id, outfit_id)
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            event_name TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_events_user_created
        ON events(user_id, created_at);

        CREATE INDEX IF NOT EXISTS idx_events_name_created
        ON events(event_name, created_at);

        CREATE TABLE IF NOT EXISTS aarrr_dataset (
            user_code TEXT PRIMARY KEY,
            first_contact_at TEXT NOT NULL,
            scenario_completed INTEGER NOT NULL,
            time_to_result_min REAL NOT NULL,
            avg_scenarios REAL NOT NULL,
            retention_d1 INTEGER NOT NULL,
            retention_d7 INTEGER NOT NULL,
            retention_d30 INTEGER NOT NULL,
            ai_stylist_used INTEGER NOT NULL,
            session_length_min REAL NOT NULL,
            bot_requests_count INTEGER NOT NULL,
            ai_usage_count INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS app_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ai_quotas (
            user_id INTEGER PRIMARY KEY,
            used_count INTEGER NOT NULL DEFAULT 0,
            limit_count INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS bot_messages (
            user_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (chat_id, message_id)
        );
        """
    )
    conn.commit()


def touch_user(
    user_id: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> None:
    now = _utcnow()
    conn = _get_conn()
    conn.execute(
        """
        INSERT INTO users (user_id, username, first_name, last_name, created_at, last_seen_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name,
            last_name = excluded.last_name,
            last_seen_at = excluded.last_seen_at
        """,
        (user_id, username, first_name, last_name, now, now),
    )
    conn.commit()


def record_event(user_id: int | None, event_name: str, payload: dict[str, Any] | None = None) -> None:
    now = _utcnow()
    conn = _get_conn()
    conn.execute(
        """
        INSERT INTO events (user_id, event_name, payload_json, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, event_name, json.dumps(payload or {}, ensure_ascii=False), now),
    )
    if user_id is not None:
        conn.execute(
            "UPDATE users SET last_seen_at = ? WHERE user_id = ?",
            (now, user_id),
        )
    conn.commit()


def track_bot_message(user_id: int, chat_id: int, message_id: int) -> None:
    conn = _get_conn()
    conn.execute(
        """
        INSERT OR IGNORE INTO bot_messages (user_id, chat_id, message_id, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, chat_id, message_id, _utcnow()),
    )
    conn.commit()


def get_tracked_bot_messages(user_id: int) -> list[dict[str, int]]:
    rows = _get_conn().execute(
        """
        SELECT chat_id, message_id
        FROM bot_messages
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,),
    ).fetchall()
    return [{"chat_id": int(row["chat_id"]), "message_id": int(row["message_id"])} for row in rows]


def clear_tracked_bot_messages(user_id: int) -> None:
    conn = _get_conn()
    conn.execute("DELETE FROM bot_messages WHERE user_id = ?", (user_id,))
    conn.commit()


def get_ai_quota(user_id: int) -> dict[str, int]:
    conn = _get_conn()
    limit = max(0, int(settings.AI_FREE_LIMIT))
    row = conn.execute(
        "SELECT used_count, limit_count FROM ai_quotas WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if row is None:
        return {"used": 0, "limit": limit, "remaining": limit}
    used = int(row["used_count"])
    current_limit = max(limit, int(row["limit_count"]))
    return {"used": used, "limit": current_limit, "remaining": max(0, current_limit - used)}


def can_use_ai(user_id: int) -> bool:
    return get_ai_quota(user_id)["remaining"] > 0


def consume_ai_quota(user_id: int, scenario: str) -> dict[str, int]:
    conn = _get_conn()
    now = _utcnow()
    quota = get_ai_quota(user_id)
    new_used = quota["used"] + 1
    conn.execute(
        """
        INSERT INTO ai_quotas (user_id, used_count, limit_count, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            used_count = excluded.used_count,
            limit_count = excluded.limit_count,
            updated_at = excluded.updated_at
        """,
        (user_id, new_used, quota["limit"], now),
    )
    conn.commit()
    record_event(
        user_id,
        "ai_quota_consumed",
        {"scenario": scenario, "used": new_used, "limit": quota["limit"]},
    )
    return {"used": new_used, "limit": quota["limit"], "remaining": max(0, quota["limit"] - new_used)}


def save_outfit(user_id: int, outfit: Outfit) -> bool:
    conn = _get_conn()
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO saved_outfits (user_id, outfit_id, outfit_snapshot, saved_at)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, outfit.id, outfit.model_dump_json(), _utcnow()),
    )
    conn.commit()
    if cursor.rowcount:
        record_event(user_id, "outfit_saved", {"outfit_id": outfit.id})
        return True
    return False


def get_saved(user_id: int) -> list[Outfit]:
    rows = _get_conn().execute(
        """
        SELECT outfit_snapshot
        FROM saved_outfits
        WHERE user_id = ?
        ORDER BY saved_at DESC
        """,
        (user_id,),
    ).fetchall()
    return [Outfit(**json.loads(row["outfit_snapshot"])) for row in rows]


def clear_saved(user_id: int) -> None:
    conn = _get_conn()
    conn.execute("DELETE FROM saved_outfits WHERE user_id = ?", (user_id,))
    conn.commit()
    record_event(user_id, "saved_cleared")


def get_profile(user_id: int) -> UserProfile | None:
    row = _get_conn().execute(
        "SELECT * FROM profiles WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if row is None:
        return None

    return UserProfile(
        user_id=row["user_id"],
        gender=row["gender"],
        style=row["style"],
        budget=row["budget"],
        preferred_colors=json.loads(row["preferred_colors"]),
        preferred_styles=json.loads(row["preferred_styles"]),
        disliked_items=json.loads(row["disliked_items"]),
        key_items=json.loads(row["key_items"]),
    )


def upsert_profile(user_id: int, **updates: Any) -> UserProfile:
    current = get_profile(user_id) or UserProfile(user_id=user_id)
    data = current.model_dump()

    for key, value in updates.items():
        if key in data and value is not None:
            data[key] = value

    profile = UserProfile(**data)
    conn = _get_conn()
    conn.execute(
        """
        INSERT INTO profiles (
            user_id, gender, style, budget,
            preferred_colors, preferred_styles, disliked_items, key_items, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            gender = excluded.gender,
            style = excluded.style,
            budget = excluded.budget,
            preferred_colors = excluded.preferred_colors,
            preferred_styles = excluded.preferred_styles,
            disliked_items = excluded.disliked_items,
            key_items = excluded.key_items,
            updated_at = excluded.updated_at
        """,
        (
            profile.user_id,
            profile.gender,
            profile.style,
            profile.budget,
            json.dumps(profile.preferred_colors, ensure_ascii=False),
            json.dumps(profile.preferred_styles, ensure_ascii=False),
            json.dumps(profile.disliked_items, ensure_ascii=False),
            json.dumps(profile.key_items, ensure_ascii=False),
            _utcnow(),
        ),
    )
    conn.commit()
    record_event(user_id, "profile_updated", updates)
    return profile


def get_saved_outfit_ids(user_id: int) -> set[str]:
    rows = _get_conn().execute(
        "SELECT outfit_id FROM saved_outfits WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    return {row["outfit_id"] for row in rows}


def get_all_events() -> list[dict[str, Any]]:
    rows = _get_conn().execute(
        "SELECT id, user_id, event_name, payload_json, created_at FROM events ORDER BY id ASC"
    ).fetchall()
    return [
        {
            "id": row["id"],
            "user_id": row["user_id"],
            "event_name": row["event_name"],
            "payload": json.loads(row["payload_json"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def _get_aarrr_metrics() -> dict[str, Any]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM aarrr_dataset ORDER BY user_code").fetchall()
    if not rows:
        return {
            "has_dataset": False,
            "source": "not_seeded",
            "new_users": 0,
            "avg_time_to_result_min": 0,
            "scenario_completion_rate": 0,
            "avg_scenarios": 0,
            "retention_d1": 0,
            "retention_d7": 0,
            "retention_d30": 0,
            "ai_stylist_share": 0,
            "avg_session_length_min": 0,
            "avg_bot_requests": 0,
            "ai_usage_frequency": 0,
            "cac": 0,
            "marketing_spend": 0,
        }

    def avg(field: str) -> float:
        return sum(float(row[field]) for row in rows) / len(rows)

    marketing_row = conn.execute("SELECT value FROM app_meta WHERE key = 'marketing_spend'").fetchone()
    marketing_spend = float(marketing_row["value"]) if marketing_row else 2000.0
    new_users = len(rows)
    return {
        "has_dataset": True,
        "source": "xlsx_seed",
        "new_users": new_users,
        "avg_time_to_result_min": round(avg("time_to_result_min"), 2),
        "scenario_completion_rate": round(avg("scenario_completed"), 2),
        "avg_scenarios": round(avg("avg_scenarios"), 2),
        "retention_d1": round(avg("retention_d1"), 2),
        "retention_d7": round(avg("retention_d7"), 2),
        "retention_d30": round(avg("retention_d30"), 2),
        "ai_stylist_share": round(avg("ai_stylist_used"), 2),
        "avg_session_length_min": round(avg("session_length_min"), 2),
        "avg_bot_requests": round(avg("bot_requests_count"), 2),
        "ai_usage_frequency": round(avg("ai_usage_count"), 2),
        "cac": round(marketing_spend / new_users, 2) if new_users else 0,
        "marketing_spend": marketing_spend,
    }


def _parse_event_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _average(values: list[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0


def _get_aarrr_event_metrics(events: list[dict[str, Any]], total_users: int) -> dict[str, Any]:
    """Считает Excel/AARRR-метрики из реальных событий бота.

    `aarrr_dataset` нужен для презентационного сида, а этот блок показывает, что те же
    показатели можно добывать из нормального event stream без ручной правки Excel.
    """
    conn = _get_conn()
    marketing_row = conn.execute("SELECT value FROM app_meta WHERE key = 'marketing_spend'").fetchone()
    marketing_spend = float(marketing_row["value"]) if marketing_row else 0.0

    by_user: dict[int, list[dict[str, Any]]] = defaultdict(list)
    counts = Counter(event["event_name"] for event in events)
    for event in events:
        if event["user_id"] is not None:
            by_user[int(event["user_id"])].append(event)

    completion_flags: list[int] = []
    time_to_result: list[float] = []
    scenarios_per_user: list[float] = []
    session_lengths: list[float] = []
    bot_requests: list[int] = []
    ai_usage: list[int] = []
    ai_user_flags: list[int] = []
    retention_flags = {1: [], 7: [], 30: []}

    def is_ai_event(event: dict[str, Any]) -> bool:
        if event["event_name"] == "ai_item_outfits_generated":
            return True
        if event["event_name"] == "review_completed":
            return event["payload"].get("source") == "deepseek"
        return False

    for user_events in by_user.values():
        user_events = sorted(user_events, key=lambda event: event["created_at"])
        summary = next((event["payload"] for event in user_events if event["event_name"] == "session_summary"), None)
        first_dt = _parse_event_dt(user_events[0]["created_at"])
        if summary and isinstance(summary.get("session_length_min"), (int, float)):
            session_lengths.append(float(summary["session_length_min"]))
        elif first_dt:
            first_day_events = [
                event for event in user_events if event["created_at"][:10] == user_events[0]["created_at"][:10]
            ]
            last_same_day = _parse_event_dt(first_day_events[-1]["created_at"])
            if last_same_day:
                session_lengths.append(round((last_same_day - first_dt).total_seconds() / 60, 2))

        scenario_starts = [event for event in user_events if event["event_name"] == "quiz_started"]
        result_events = [event for event in user_events if event["event_name"] == "results_viewed"]
        completion_flags.append(1 if result_events else 0)
        if summary and isinstance(summary.get("avg_scenarios"), (int, float)):
            scenarios_per_user.append(float(summary["avg_scenarios"]))
        else:
            scenarios_per_user.append(float(len(scenario_starts)))
        if summary and isinstance(summary.get("bot_requests_count"), (int, float)):
            bot_requests.append(int(summary["bot_requests_count"]))
        else:
            bot_requests.append(sum(1 for event in user_events if event["event_name"] == "bot_started"))

        user_ai_count = (
            int(summary["ai_usage_count"])
            if summary and isinstance(summary.get("ai_usage_count"), (int, float))
            else sum(1 for event in user_events if is_ai_event(event))
        )
        ai_usage.append(user_ai_count)
        ai_user_flags.append(1 if user_ai_count else 0)

        for result in result_events:
            if summary and isinstance(summary.get("time_to_result_min"), (int, float)):
                continue
            payload_time = result["payload"].get("time_to_result_min")
            if isinstance(payload_time, (int, float)):
                time_to_result.append(float(payload_time))
                continue
            result_dt = _parse_event_dt(result["created_at"])
            previous_starts = [
                _parse_event_dt(start["created_at"])
                for start in scenario_starts
                if start["created_at"] <= result["created_at"]
            ]
            previous_starts = [dt for dt in previous_starts if dt is not None]
            if result_dt and previous_starts:
                time_to_result.append(round((result_dt - previous_starts[-1]).total_seconds() / 60, 2))

        if summary and isinstance(summary.get("time_to_result_min"), (int, float)):
            time_to_result.append(float(summary["time_to_result_min"]))

        if first_dt:
            first_day = first_dt.date()
            active_days = {
                parsed.date()
                for parsed in (_parse_event_dt(event["created_at"]) for event in user_events)
                if parsed is not None
            }
            for day in retention_flags:
                retention_flags[day].append(1 if first_day + timedelta(days=day) in active_days else 0)

    return {
        "source": "events",
        "new_users": total_users,
        "avg_time_to_result_min": _average(time_to_result),
        "scenario_completion_rate": _average(completion_flags),
        "avg_scenarios": _average(scenarios_per_user),
        "retention_d1": _average(retention_flags[1]),
        "retention_d7": _average(retention_flags[7]),
        "retention_d30": _average(retention_flags[30]),
        "ai_stylist_share": _average(ai_user_flags),
        "avg_session_length_min": _average(session_lengths),
        "avg_bot_requests": _average(bot_requests),
        "ai_usage_frequency": _average(ai_usage),
        "cac": round(marketing_spend / total_users, 2) if total_users and marketing_spend else 0,
        "marketing_spend": marketing_spend,
        "shared_outfits": counts["outfit_shared"],
        "payment_conversion": round(counts["premium_interest"] / total_users, 2) if total_users else 0,
    }


def get_metrics() -> dict[str, Any]:
    events = get_all_events()

    conn = _get_conn()
    total_users = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
    saved_total = conn.execute("SELECT COUNT(*) AS count FROM saved_outfits").fetchone()["count"]
    profiles_total = conn.execute("SELECT COUNT(*) AS count FROM profiles").fetchone()["count"]

    counts = Counter(event["event_name"] for event in events)
    daily_users: dict[int, set[str]] = defaultdict(set)
    answers_by_step: dict[str, int] = defaultdict(int)
    feedback_scores: list[int] = []
    review_feedback_scores: list[int] = []
    result_distribution: Counter[int] = Counter()
    review_distribution: Counter[int] = Counter()
    recent_comments: dict[str, list[dict[str, Any]]] = {"result": [], "review": []}

    for event in events:
        user_id = event["user_id"]
        payload = event["payload"]
        name = event["event_name"]
        if user_id is not None:
            daily_users[user_id].add(event["created_at"][:10])
        if name == "question_answered":
            step = payload.get("step", "unknown")
            answers_by_step[step] += 1
        if name == "result_feedback" and isinstance(payload.get("score"), int):
            feedback_scores.append(payload["score"])
            result_distribution[payload["score"]] += 1
        if name == "review_feedback" and isinstance(payload.get("score"), int):
            review_feedback_scores.append(payload["score"])
            review_distribution[payload["score"]] += 1
        if name in ("result_feedback_comment", "review_feedback_comment"):
            kind = "result" if name.startswith("result") else "review"
            text = payload.get("text")
            if text:
                recent_comments[kind].append({
                    "id": event["id"],
                    "score": payload.get("score"),
                    "text": text,
                    "created_at": event["created_at"],
                })

    # Сортируем по убыванию даты и оставляем последние 5 для каждого вида.
    for kind in recent_comments:
        recent_comments[kind].sort(key=lambda item: (item["created_at"], item.get("id", 0)), reverse=True)
        recent_comments[kind] = recent_comments[kind][:5]

    quiz_started = counts["quiz_started"]
    quiz_completed = counts["quiz_completed"]
    results_viewed = counts["results_viewed"]
    show_more = counts["show_more"]
    saved_rate = saved_total / results_viewed if results_viewed else 0
    repeat_users = sum(1 for days in daily_users.values() if len(days) >= 2)
    ai_quota_rows = conn.execute(
        "SELECT COUNT(*) AS users, COALESCE(SUM(used_count), 0) AS total_used FROM ai_quotas"
    ).fetchone()

    metrics = {
        "aarrr": _get_aarrr_metrics(),
        "aarrr_events": _get_aarrr_event_metrics(events, total_users),
        "users": {
            "total_unique": total_users,
            "repeat_users_7d_proxy": repeat_users,
            "profiles_completed": profiles_total,
        },
        "funnel": {
            "quiz_started": quiz_started,
            "quiz_completed": quiz_completed,
            "quiz_completion_rate": round(quiz_completed / quiz_started, 2) if quiz_started else 0,
            "result_view_rate": round(results_viewed / quiz_started, 2) if quiz_started else 0,
            "dropoff_by_step": dict(answers_by_step),
        },
        "engagement": {
            "saved_outfits_total": saved_total,
            "save_rate": round(saved_rate, 2),
            "show_more_rate": round(show_more / results_viewed, 2) if results_viewed else 0,
            "repeat_usage_rate": round(repeat_users / total_users, 2) if total_users else 0,
            "profile_completion_rate": round(profiles_total / total_users, 2) if total_users else 0,
            "weather_usage_rate": round(counts["weather_selected"] / quiz_started, 2) if quiz_started else 0,
            "weather_auto_usage_rate": round(counts["weather_auto_succeeded"] / quiz_started, 2) if quiz_started else 0,
            "weather_auto_success_rate": round(
                counts["weather_auto_succeeded"] / counts["weather_auto_attempted"], 2
            ) if counts["weather_auto_attempted"] else 0,
            "owned_item_usage_rate": round(counts["item_flow_started"] / quiz_started, 2) if quiz_started else 0,
            "outfit_check_usage_rate": round(counts["review_started"] / total_users, 2) if total_users else 0,
            "ai_free_limit": settings.AI_FREE_LIMIT,
            "ai_quota_users": ai_quota_rows["users"],
            "ai_quota_used_total": ai_quota_rows["total_used"],
        },
        "quality": {
            "reference_click_rate": round(counts["reference_opened"] / results_viewed, 2) if results_viewed else 0,
            "premium_interest_rate": round(counts["premium_interest"] / total_users, 2) if total_users else 0,
            "satisfaction_rate": round(sum(feedback_scores) / len(feedback_scores), 2) if feedback_scores else 0,
            "review_satisfaction_rate": round(sum(review_feedback_scores) / len(review_feedback_scores), 2)
            if review_feedback_scores else 0,
            "result_feedback_distribution": {
                "positive": result_distribution[5],
                "neutral": result_distribution[3],
                "negative": result_distribution[1],
            },
            "review_feedback_distribution": {
                "positive": review_distribution[5],
                "neutral": review_distribution[3],
                "negative": review_distribution[1],
            },
            "recent_feedback_comments": recent_comments,
        },
        "events": counts,
    }
    return metrics
