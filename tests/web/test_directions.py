from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.web.directions import suggest_directions  # noqa: E402


class DirectionCatalogTests(unittest.TestCase):
    def test_vague_classroom_request_returns_three_distinct_directions(self):
        result = suggest_directions("classroom-tool")

        self.assertEqual(len(result), 3)
        self.assertEqual(len({item.id for item in result}), 3)
        self.assertTrue(all(item.feeling and item.primary_interaction for item in result))

    def test_hardware_request_prioritizes_visible_connection_feedback(self):
        result = suggest_directions("hardware-interface")

        self.assertIn("连接", result[0].primary_interaction)

    def test_mini_game_request_returns_three_distinct_playable_patterns(self):
        result = suggest_directions("mini-game")

        self.assertEqual(
            [item.id for item in result],
            ["reaction-rush", "dodge-collect", "drag-puzzle"],
        )
        self.assertTrue(all(item.primary_interaction and item.tradeoff for item in result))

    def test_beginner_catalog_hides_advanced_directions_until_explicitly_requested(self):
        beginner = suggest_directions("classroom-tool")
        advanced = suggest_directions("classroom-tool", advanced=True)

        self.assertLessEqual(len(beginner), 3)
        self.assertGreaterEqual(len(advanced), len(beginner) + 2)
        self.assertTrue({item.id for item in beginner}.issubset({item.id for item in advanced}))

    def test_each_project_kind_has_two_distinct_advanced_directions(self):
        for kind in ("classroom-tool", "hardware-interface", "mini-game"):
            with self.subTest(kind=kind):
                beginner = suggest_directions(kind)
                expanded = suggest_directions(kind, advanced=True)
                extras = expanded[len(beginner) :]

                self.assertGreaterEqual(len(extras), 2)
                self.assertEqual(len({item.aesthetic for item in extras}), len(extras))
                self.assertTrue(
                    all(
                        item.feeling
                        and item.primary_interaction
                        and item.best_for
                        and item.tradeoff
                        for item in extras
                    )
                )

    def test_non_boolean_advanced_values_are_rejected(self):
        for value in ("false", 1, None):
            with self.subTest(value=value):
                with self.assertRaisesRegex(TypeError, "advanced must be a boolean"):
                    suggest_directions("classroom-tool", advanced=value)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
