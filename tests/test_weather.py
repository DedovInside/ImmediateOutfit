from __future__ import annotations

import unittest

from services.weather import temp_to_bucket


class TempToBucketTests(unittest.TestCase):
    def test_rain_overrides_temperature(self) -> None:
        self.assertEqual(temp_to_bucket(25.0, "Rain"), "rain")
        self.assertEqual(temp_to_bucket(-5.0, "Snow"), "rain")
        self.assertEqual(temp_to_bucket(15.0, "Drizzle"), "rain")
        self.assertEqual(temp_to_bucket(15.0, "Thunderstorm"), "rain")

    def test_warm_threshold(self) -> None:
        self.assertEqual(temp_to_bucket(18.0, "Clear"), "warm")
        self.assertEqual(temp_to_bucket(25.5, "Clouds"), "warm")

    def test_mild_threshold(self) -> None:
        self.assertEqual(temp_to_bucket(10.0, "Clouds"), "mild")
        self.assertEqual(temp_to_bucket(17.9, "Clear"), "mild")

    def test_cold_threshold(self) -> None:
        self.assertEqual(temp_to_bucket(9.9, "Clouds"), "cold")
        self.assertEqual(temp_to_bucket(-15.0, "Clear"), "cold")

    def test_case_insensitive_condition(self) -> None:
        self.assertEqual(temp_to_bucket(20.0, "rain"), "rain")
        self.assertEqual(temp_to_bucket(20.0, "RAIN"), "rain")


if __name__ == "__main__":
    unittest.main()
