from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "runtime" / "chatmaker" / "catalog.py"


def load_catalog():
    if not CATALOG_PATH.is_file():
        return None
    spec = importlib.util.spec_from_file_location("chatmaker_catalog", CATALOG_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()

    def test_catalog_runtime_exists(self):
        self.assertIsNotNone(self.catalog, "catalog runtime is missing")

    def test_search_finds_a_component_by_chinese_alias(self):
        self.assertIsNotNone(self.catalog, "catalog runtime is missing")

        result = self.catalog.search_catalog("继电器", kind="component", project_root=ROOT)

        self.assertTrue(result["success"], result)
        self.assertEqual(result["match_count"], 1)
        self.assertEqual(result["matches"][0]["id"], "one-channel-relay-module-5v")
        self.assertEqual(result["matches"][0]["kind"], "component")

    def test_get_returns_the_full_record_and_evidence_gates(self):
        self.assertIsNotNone(self.catalog, "catalog runtime is missing")

        result = self.catalog.get_catalog_record(
            "ws2812b-addressable-rgb", project_root=ROOT
        )

        self.assertTrue(result["success"], result)
        self.assertEqual(result["record"]["id"], "ws2812b-addressable-rgb")
        self.assertTrue(result["record"]["identification"])
        self.assertTrue(result["record"]["constraints"])
        self.assertTrue(result["record"]["example_files"])
        self.assertEqual(result["record"]["verification"]["code_compiled"]["status"], "verified")
        self.assertEqual(
            result["record"]["verification"]["physical_effect_verified"]["status"],
            "unverified",
        )

    def test_get_loads_only_the_requested_record_path(self):
        self.assertIsNotNone(self.catalog, "catalog runtime is missing")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "packs" / "components" / "target-record.yaml"
            other = root / "packs" / "components" / "other-record.yaml"
            root.joinpath("packs", "boards").mkdir(parents=True)
            target.parent.mkdir(parents=True, exist_ok=True)
            root.joinpath("packs", "recipes").mkdir(parents=True)
            target.write_text(
                yaml.safe_dump(
                    {
                        "schema_version": "1.0",
                        "kind": "component",
                        "id": "target-record",
                        "name": "Target Record",
                        "category": "output",
                        "interface": "digital",
                        "summary": "Only this file should be loaded for catalog_get.",
                        "verification": {},
                    },
                    allow_unicode=True,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            other.write_text(
                yaml.safe_dump(
                    {
                        "schema_version": "1.0",
                        "kind": "component",
                        "id": "other-record",
                        "name": "Other Record",
                        "category": "input",
                        "interface": "analog",
                        "summary": "This file must stay unread during exact get.",
                        "verification": {},
                    },
                    allow_unicode=True,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            original = self.catalog.load_record
            loaded_paths: list[str] = []

            def only_target(path):
                loaded_paths.append(Path(path).name)
                if Path(path).name != "target-record.yaml":
                    raise AssertionError(f"catalog_get loaded an unrelated file: {path}")
                return original(path)

            self.catalog.load_record = only_target
            try:
                result = self.catalog.get_catalog_record("target-record", project_root=root)
            finally:
                self.catalog.load_record = original

        self.assertTrue(result["success"], result)
        self.assertEqual(loaded_paths, ["target-record.yaml"])
        self.assertEqual(result["record"]["id"], "target-record")

    def test_json_cli_searches_the_checked_in_catalog(self):
        self.assertIsNotNone(self.catalog, "catalog runtime is missing")
        environment = dict(os.environ)
        environment["PYTHONIOENCODING"] = "cp1252"

        completed = subprocess.run(
            [
                sys.executable,
                str(CATALOG_PATH),
                "--request-json",
                json.dumps({"action": "search", "query": "电位器", "kind": "component"}),
            ],
            text=True,
            capture_output=True,
            cwd=ROOT,
            env=environment,
            timeout=10,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["success"], payload)
        self.assertEqual(payload["matches"][0]["id"], "linear-potentiometer-10k")


if __name__ == "__main__":
    unittest.main()
