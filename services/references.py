"""
Работа с локальными референсами образов.
"""
from __future__ import annotations

from pathlib import Path

from models.outfit import Outfit

BASE_DIR = Path(__file__).resolve().parent.parent
REFERENCE_ASSETS_DIR = BASE_DIR / "assets" / "outfit_references"
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGES_PER_REFERENCE = 10


def get_reference_folder(outfit: Outfit) -> Path | None:
    if outfit.reference and outfit.reference.local_folder:
        folder = BASE_DIR / outfit.reference.local_folder
    elif outfit.source == "team_curated_txt":
        folder = REFERENCE_ASSETS_DIR / outfit.id
    else:
        return None
    try:
        resolved = folder.resolve()
        root = REFERENCE_ASSETS_DIR.resolve()
    except OSError:
        return None
    if root not in (resolved, *resolved.parents):
        return None
    return resolved


def get_reference_images(outfit: Outfit) -> list[Path]:
    folder = get_reference_folder(outfit)
    if not folder or not folder.exists() or not folder.is_dir():
        return []
    images = [
        item for item in folder.iterdir()
        if item.is_file() and item.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
    ]
    return sorted(images, key=lambda path: path.name.lower())[:MAX_IMAGES_PER_REFERENCE]
