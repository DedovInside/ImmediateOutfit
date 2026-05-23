"""
SQLite-хранилище пользователей, профилей, сохранений и событий.
"""
from __future__ import annotations

import json
import sqlite3
from collections import Counter
from collections import defaultdict
from datetime import UTC, datetime
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

    metrics = {
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
