from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from services import storage
from services.catalog import find_outfit


class StorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        storage.DB_PATH = Path(self.temp_dir.name) / "test.db"
        storage.init_db()
        storage.touch_user(1, username="alice", first_name="Alice")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_profile_roundtrip(self) -> None:
        profile = storage.upsert_profile(
            1,
            gender="female",
            style="casual",
            budget="medium",
            preferred_colors=["black", "beige"],
            key_items=["white shirt"],
        )
        self.assertEqual(profile.gender, "female")
        loaded = storage.get_profile(1)
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded.preferred_colors, ["black", "beige"])

    def test_saved_outfit_and_metrics(self) -> None:
        outfit = find_outfit("m_001")
        self.assertIsNotNone(outfit)
        assert outfit is not None

        saved = storage.save_outfit(1, outfit)
        self.assertTrue(saved)
        self.assertEqual(len(storage.get_saved(1)), 1)

        storage.record_event(1, "quiz_started")
        storage.record_event(1, "weather_selected", {"value": "mild"})
        storage.record_event(1, "quiz_completed")
        storage.record_event(1, "results_viewed")
        metrics = storage.get_metrics()

        self.assertEqual(metrics["users"]["total_unique"], 1)
        self.assertEqual(metrics["engagement"]["saved_outfits_total"], 1)
        self.assertEqual(metrics["funnel"]["quiz_started"], 1)


if __name__ == "__main__":
    unittest.main()
