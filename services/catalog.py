"""
Загрузка каталога образов и curated-метаданных.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from models.outfit import Outfit

BASE_DIR = Path(__file__).resolve().parent.parent
OUTFITS_PATH = BASE_DIR / "data" / "outfits.json"
CURATION_PATH = BASE_DIR / "data" / "curation.json"
TEAM_OUTFITS_PATH = BASE_DIR / "data" / "team_outfits.json"


def _load_json(path: Path) -> object:
    with open(path, encoding="utf-8") as file:
        return json.load(file)


@lru_cache(maxsize=1)
def get_outfits() -> list[Outfit]:
    raw_outfits = _load_json(OUTFITS_PATH)
    curation_raw = _load_json(CURATION_PATH) if CURATION_PATH.exists() else {}
    curation = curation_raw if isinstance(curation_raw, dict) else {}
    team_raw = _load_json(TEAM_OUTFITS_PATH) if TEAM_OUTFITS_PATH.exists() else []
    team_outfits = team_raw if isinstance(team_raw, list) else []

    outfits: list[Outfit] = []
    for item in raw_outfits:
        extra = curation.get(item["id"], {})
        outfits.append(Outfit(**item, **extra))
    for item in team_outfits:
        outfits.append(Outfit(**item))
    return outfits


def find_outfit(outfit_id: str) -> Outfit | None:
    return next((outfit for outfit in get_outfits() if outfit.id == outfit_id), None)

