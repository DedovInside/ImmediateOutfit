from __future__ import annotations

import unittest

from services.catalog import get_outfits
from services.recommender import recommend, review_user_outfit


class RecommenderTests(unittest.TestCase):
    def test_recommend_returns_matching_gender(self) -> None:
        results = recommend(
            {
                "gender": "male",
                "occasion": "study_work",
                "weather": "mild",
                "activity": "calm",
                "priority": "comfort",
                "budget": "low",
                "style": "casual",
            },
            get_outfits(),
        )
        self.assertTrue(results)
        self.assertTrue(all("male" in result.outfit.gender for result in results))

    def test_review_user_outfit_is_structured(self) -> None:
        review = review_user_outfit("черная водолазка, голубые джинсы, белые кеды")
        self.assertTrue(review.headline)
        self.assertTrue(review.strengths)
        self.assertTrue(review.suggestions)


if __name__ == "__main__":
    unittest.main()
