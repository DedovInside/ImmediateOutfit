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

    def test_duplicate_save_is_idempotent(self) -> None:
        outfit = find_outfit("m_001")
        assert outfit is not None
        self.assertTrue(storage.save_outfit(1, outfit))
        self.assertFalse(storage.save_outfit(1, outfit))
        self.assertEqual(len(storage.get_saved(1)), 1)

    def test_clear_saved_empties_list(self) -> None:
        outfit = find_outfit("m_001")
        assert outfit is not None
        storage.save_outfit(1, outfit)
        self.assertEqual(len(storage.get_saved(1)), 1)
        storage.clear_saved(1)
        self.assertEqual(storage.get_saved(1), [])
        self.assertEqual(storage.get_saved_outfit_ids(1), set())

    def test_metrics_dropoff_and_completion_rate(self) -> None:
        storage.record_event(1, "quiz_started")
        storage.record_event(1, "question_answered", {"step": "gender", "value": "male"})
        storage.record_event(1, "question_answered", {"step": "occasion", "value": "study_work"})
        storage.record_event(1, "question_answered", {"step": "weather", "value": "mild"})
        storage.record_event(1, "quiz_completed")
        storage.record_event(1, "results_viewed")

        metrics = storage.get_metrics()
        self.assertEqual(metrics["funnel"]["dropoff_by_step"]["gender"], 1)
        self.assertEqual(metrics["funnel"]["dropoff_by_step"]["weather"], 1)
        self.assertEqual(metrics["funnel"]["quiz_completion_rate"], 1.0)
        self.assertEqual(metrics["funnel"]["result_view_rate"], 1.0)

    def test_feedback_distribution_counts_each_bucket(self) -> None:
        for score in [5, 5, 5, 3, 1]:
            storage.record_event(1, "result_feedback", {"score": score})
        for score in [5, 3, 1, 1]:
            storage.record_event(1, "review_feedback", {"score": score})

        dist = storage.get_metrics()["quality"]
        self.assertEqual(dist["result_feedback_distribution"], {"positive": 3, "neutral": 1, "negative": 1})
        self.assertEqual(dist["review_feedback_distribution"], {"positive": 1, "neutral": 1, "negative": 2})

    def test_recent_feedback_comments_collected(self) -> None:
        storage.record_event(1, "result_feedback_comment", {"score": 1, "text": "слишком спортивно"})
        storage.record_event(1, "result_feedback_comment", {"score": 3, "text": "мало вариантов"})
        storage.record_event(1, "review_feedback_comment", {"score": 1, "text": "разбор поверхностный"})

        comments = storage.get_metrics()["quality"]["recent_feedback_comments"]
        self.assertEqual(len(comments["result"]), 2)
        self.assertEqual(len(comments["review"]), 1)
        # последний по времени — первым в списке
        self.assertEqual(comments["result"][0]["text"], "мало вариантов")
        self.assertEqual(comments["review"][0]["text"], "разбор поверхностный")


if __name__ == "__main__":
    unittest.main()
