from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
BOARD_ID = "idmc-0001-starcore-v4-2-2"
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.packs import canonical_verification_snapshot  # noqa: E402


def load_yaml(relative: str) -> dict:
    return yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))


def load_sync_module():
    path = ROOT / "scripts" / "sync_starcore_evidence.py"
    spec = importlib.util.spec_from_file_location("sync_starcore_evidence", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StarcoreEvidenceNormalizationTests(unittest.TestCase):
    def test_board_aggregate_does_not_hide_feature_boundaries(self):
        board = load_yaml(f"packs/boards/{BOARD_ID}.yaml")
        self.assertEqual(
            {item["status"] for item in board["toolchains"]},
            {"verified_supported"},
        )
        self.assertEqual(
            board["toolchain_selection"]["policy"],
            "reuse-any-usable-installation",
        )
        self.assertEqual(
            board["verification"]["physical_effect_verified"]["status"],
            "not_applicable",
        )
        features = {item["feature_id"]: item for item in board["feature_verification"]}
        self.assertEqual(
            features["passive-buzzer"]["verification"]["physical_effect_verified"]["status"],
            "verified",
        )
        self.assertEqual(
            features["passive-buzzer"]["verification"]["physical_effect_verified"]["method"],
            "user-confirmation",
        )
        for button_id in ("button-a", "button-b"):
            self.assertEqual(
                features[button_id]["verification"]["physical_effect_verified"]["status"],
                "unverified",
            )

    def test_self_test_and_oled_keep_case_and_effect_gates_separate(self):
        self_test = load_yaml("packs/recipes/starcore-onboard-self-test.yaml")
        oled = load_yaml("packs/recipes/starcore-idmd-0021-oled-message.yaml")
        self.assertEqual(self_test["verification"]["serial_evidence"]["status"], "verified")
        self.assertEqual(
            self_test["verification"]["physical_effect_verified"]["status"],
            "not_applicable",
        )
        self.assertEqual(oled["verification"]["firmware_uploaded"]["status"], "verified")
        self.assertEqual(oled["verification"]["display_proxy_evidence"]["status"], "verified")
        self.assertEqual(
            oled["verification"]["display_proxy_evidence"]["method"],
            "serial-proxy",
        )
        self.assertEqual(oled["verification"]["physical_effect_verified"]["status"], "verified")
        self.assertEqual(
            oled["verification"]["physical_effect_verified"]["method"],
            "user-confirmation",
        )

    def test_generated_readme_and_knowledge_summaries_are_current(self):
        result = load_sync_module().synchronize(ROOT, write=False)
        self.assertTrue(result["success"], result["errors"])

    def test_canonical_snapshot_includes_scoped_feature_and_effect_gates(self):
        snapshot, digest = canonical_verification_snapshot(ROOT / "packs")
        records = {(item["kind"], item["id"]): item for item in snapshot}
        board = records[("board", BOARD_ID)]
        self_test = records[("recipe", "starcore-onboard-self-test")]
        self.assertIn("feature_verification", board)
        self.assertIn("effect_verification", self_test)
        self.assertEqual(len(digest), 64)


if __name__ == "__main__":
    unittest.main()
