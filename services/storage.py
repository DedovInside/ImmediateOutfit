"""
In-memory хранилище сохранённых образов пользователей.
На уровне MVP - dict в памяти. При перезапуске данные теряются.
"""
from __future__ import annotations

from models.outfit import Outfit

# {user_id: [Outfit, ...]}
_saved: dict[int, list[Outfit]] = {}


def save_outfit(user_id: int, outfit: Outfit) -> bool:
    """Сохранить образ. Возвращает False, если уже сохранён."""
    if user_id not in _saved:
        _saved[user_id] = []
    if any(o.id == outfit.id for o in _saved[user_id]):
        return False
    _saved[user_id].append(outfit)
    return True


def get_saved(user_id: int) -> list[Outfit]:
    """Получить список сохранённых образов."""
    return _saved.get(user_id, [])


def clear_saved(user_id: int) -> None:
    """Очистить сохранённые образы."""
    _saved.pop(user_id, None)

