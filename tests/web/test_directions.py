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


if __name__ == "__main__":
    unittest.main()
