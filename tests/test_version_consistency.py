from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_checker():
    path = ROOT / "scripts" / "check_version_consistency.py"
    spec = importlib.util.spec_from_file_location("chatmaker_version_consistency", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class VersionConsistencyTests(unittest.TestCase):
    def test_public_version_matches_user_facing_documents(self):
        checker = load_checker()
        self.assertEqual(checker.public_version(ROOT), "0.2.0-beta.1")
        self.assertEqual(checker.check(ROOT), [])


if __name__ == "__main__":
    unittest.main()
