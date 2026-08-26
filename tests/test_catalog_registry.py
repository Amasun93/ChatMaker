from __future__ import annotations

import importlib
import importlib.util
import json
from pathlib import Path
import sys
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.catalog_registry import (
    ALLOWED_KNOWLEDGE_PACKS,
    BOARD_REGISTRATIONS,
    COMPONENT_REGISTRATIONS,
)
from chatmaker.packs import validate_repository


def load_sync_script():
    path = ROOT / "scripts" / "sync_catalog_registry.py"
    spec = importlib.util.spec_from_file_location("sync_catalog_registry", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CatalogRegistryTests(unittest.TestCase):
    def test_all_canonical_records_validate_after_registry_changes(self):
        report = validate_repository(ROOT / "packs", ROOT / "packs" / "schemas")
        self.assertTrue(report.ok, "\n".join(report.errors))

    def test_generated_registry_is_in_sync_with_single_record_directories(self):
        sync = load_sync_script()
        expected = sync.canonical_bytes(sync.build_registry(ROOT))
        actual = (ROOT / "runtime" / "chatmaker" / "catalog_registry.json").read_bytes()

        self.assertEqual(actual, expected)
        self.assertEqual(set(BOARD_REGISTRATIONS), {path.stem for path in (ROOT / "packs" / "boards").glob("*.yaml")})
        self.assertEqual(set(COMPONENT_REGISTRATIONS), {path.stem for path in (ROOT / "packs" / "components").glob("*.yaml")})

    def test_registered_board_runtime_and_mechanics_references_are_real(self):
        scripts = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]
        for board_id, registration in BOARD_REGISTRATIONS.items():
            with self.subTest(board_id=board_id):
                cli = registration["runtime_cli"]
                module = registration["runtime_module"]
                if cli is None:
                    self.assertIsNone(module)
                else:
                    self.assertIn(cli, scripts)
                    self.assertEqual(scripts[cli].split(":", 1)[0], module)
                    importlib.import_module(module)
                mechanics = registration["mechanics"]
                if mechanics["status"] == "profile-available":
                    profile = ROOT / mechanics["profile_path"]
                    self.assertTrue(profile.is_file())
                    self.assertEqual(json.loads(profile.read_text(encoding="utf-8"))["board_id"], board_id)
                else:
                    self.assertIsNone(mechanics["profile_path"])

    def test_knowledge_allowlist_is_derived_from_registered_indexes(self):
        expected = {
            registration["knowledge"]["pack_id"]: board_id
            for board_id, registration in BOARD_REGISTRATIONS.items()
            if registration["knowledge"] is not None
        }
        self.assertEqual(ALLOWED_KNOWLEDGE_PACKS, expected)


if __name__ == "__main__":
    unittest.main()
