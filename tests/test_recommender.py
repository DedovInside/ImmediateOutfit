from __future__ import annotations

import unittest

from models.profile import UserProfile
from services.catalog import get_outfits
from services.recommender import recommend, review_user_outfit


BASE_ANSWERS = {
    "gender": "male",
    "occasion": "study_work",
    "weather": "mild",
    "activity": "calm",
    "priority": "comfort",
    "budget": "low",
    "style": "casual",
}


class RecommenderTests(unittest.TestCase):
    def test_recommend_returns_matching_gender(self) -> None:
        results = recommend(BASE_ANSWERS, get_outfits())
        self.assertTrue(results)
        self.assertTrue(all("male" in result.outfit.gender for result in results))

    def test_review_user_outfit_is_structured(self) -> None:
        review = review_user_outfit("черная водолазка, голубые джинсы, белые кеды")
        self.assertTrue(review.headline)
        self.assertTrue(review.strengths)
        self.assertTrue(review.suggestions)

    def test_shown_ids_excludes_previous(self) -> None:
        outfits = get_outfits()
        first = recommend(BASE_ANSWERS, outfits, limit=1)
        self.assertTrue(first)
        shown_id = first[0].outfit.id
        second = recommend(BASE_ANSWERS, outfits, shown_ids=[shown_id], limit=1)
        self.assertTrue(second)
        self.assertNotEqual(second[0].outfit.id, shown_id)

    def test_item_anchor_lifts_matching_outfit(self) -> None:
        outfits = get_outfits()
        target = next(
            outfit for outfit in outfits
            if "male" in outfit.gender
            and "study_work" in outfit.occasion
            and "рубашка" in " ".join(outfit.items.values()).lower()
        )

        def _score_for(outfit_id: str, anchor: str | None) -> int | None:
            results = recommend(BASE_ANSWERS, outfits, item_anchor=anchor, limit=len(outfits))
            for result in results:
                if result.outfit.id == outfit_id:
                    return result.score
            return None

        baseline_score = _score_for(target.id, None)
        anchored_score = _score_for(target.id, "белая рубашка")
        self.assertIsNotNone(baseline_score)
        self.assertIsNotNone(anchored_score)
        assert baseline_score is not None and anchored_score is not None
        self.assertGreater(anchored_score, baseline_score)

    def test_profile_preferred_colors_boost_score(self) -> None:
        outfits = get_outfits()
        plain_top = recommend(BASE_ANSWERS, outfits, limit=1)[0]
        profile = UserProfile(user_id=1, preferred_colors=["черн", "сер", "беж"])
        boosted_top = recommend(BASE_ANSWERS, outfits, profile=profile, limit=1)[0]
        # color-bonus может не сменить топ, но как минимум не должен уронить итоговый скор
        self.assertGreaterEqual(boosted_top.score, plain_top.score)

    def test_catalog_includes_team_curated_outfits(self) -> None:
        outfits = get_outfits()
        team_outfits = [outfit for outfit in outfits if outfit.source == "team_curated_txt"]
        self.assertGreaterEqual(len(team_outfits), 80)
        self.assertTrue(any(outfit.palette for outfit in team_outfits))
        self.assertTrue(any(outfit.purchase_links for outfit in team_outfits))

    def test_mood_lifts_smart_classic_outfits(self) -> None:
        outfits = get_outfits()
        answers = {
            **BASE_ANSWERS,
            "gender": "female",
            "occasion": "event",
            "weather": "mild",
            "activity": "mixed",
            "priority": "impressive",
            "budget": "medium",
            "style": "classic",
        }
        neutral_top = recommend({**answers, "mood": "neutral"}, outfits, limit=1)[0]
        smart_top = recommend({**answers, "mood": "smart"}, outfits, limit=1)[0]
        self.assertGreaterEqual(smart_top.score, neutral_top.score)
        self.assertIn("classic", smart_top.outfit.style)


if __name__ == "__main__":
    unittest.main()
