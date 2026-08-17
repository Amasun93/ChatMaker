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
STARCORE_BOARD_ID = "idmc-0001-starcore-v4-2-2"
OWNED_STARCORE_COMPONENTS = {
    "idmd-0001-starcore-rgb-light": "IDMD-0001",
    "idmd-0002-starcore-serial-mp3": "IDMD-0002",
    "idmd-0021-starcore-oled-1-3": "IDMD-0021",
    "idms-0001-starcore-button": "IDMS-0001",
    "idms-0003-starcore-potentiometer": "IDMS-0003",
    "idms-0008-starcore-dht11": "IDMS-0008",
    "idms-0009-starcore-ultrasonic": "IDMS-0009",
}


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

    def test_get_uses_stable_id_even_when_filename_differs(self):
        self.assertIsNotNone(self.catalog, "catalog runtime is missing")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "packs" / "components" / "target-record-v2.yaml"
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
                        "summary": "This record should resolve by stable ID, not filename.",
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
                if Path(path).name != "target-record-v2.yaml":
                    raise AssertionError(f"catalog_get loaded an unrelated file: {path}")
                return original(path)

            self.catalog.load_record = only_target
            try:
                result = self.catalog.get_catalog_record("target-record", project_root=root)
            finally:
                self.catalog.load_record = original

        self.assertTrue(result["success"], result)
        self.assertEqual(loaded_paths, ["target-record-v2.yaml"])
        self.assertEqual(result["record"]["id"], "target-record")
        self.assertEqual(result["source_path"], "packs/components/target-record-v2.yaml")

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

    def test_get_does_not_yaml_parse_unrelated_record_bodies(self):
        self.assertIsNotNone(self.catalog, "catalog runtime is missing")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "packs" / "components" / "target-record-v2.yaml"
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
                        "summary": "This target should still load normally.",
                        "verification": {},
                    },
                    allow_unicode=True,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            other.write_text(
                "id: other-record\n"
                "name: Other Record\n"
                "broken:\n"
                "  [this is not valid yaml\n",
                encoding="utf-8",
            )

            result = self.catalog.get_catalog_record("target-record", project_root=root)

        self.assertTrue(result["success"], result)
        self.assertEqual(result["record"]["id"], "target-record")
        self.assertEqual(result["source_path"], "packs/components/target-record-v2.yaml")

    def test_open_board_returns_reverse_indexes_and_wiki_summaries(self):
        self.assertIsNotNone(self.catalog, "catalog runtime is missing")

        result = self.catalog.open_board("arduino-nano-classic", project_root=ROOT)

        self.assertTrue(result["success"], result)
        self.assertEqual(result["action"], "open_board")
        self.assertEqual(result["board"]["id"], "arduino-nano-classic")
        self.assertEqual(result["source_path"], "packs/boards/arduino-nano-classic.yaml")
        component_ids = [item["id"] for item in result["components"]]
        recipe_ids = [item["id"] for item in result["recipes"]]
        self.assertIn("basic-led", component_ids)
        self.assertIn("analog-light-sensor-module", component_ids)
        self.assertIn("nano-blink-built-in", recipe_ids)
        self.assertIn("nano-light-led", recipe_ids)
        self.assertNotIn("uno-blink-built-in", recipe_ids)
        self.assertEqual(
            set(result["components"][0]),
            {"id", "kind", "name", "aliases", "category", "interface", "summary", "verification"},
        )
        self.assertEqual(len(result["knowledge"]["sections"]), 8)
        self.assertEqual(result["knowledge"]["sections"][0]["section_id"], "start-here")

    def test_starcore_open_board_contains_seven_distinct_owned_components(self):
        result = self.catalog.open_board(STARCORE_BOARD_ID, project_root=ROOT)

        self.assertTrue(result["success"], result)
        component_ids = {item["id"] for item in result["components"]}
        self.assertTrue(set(OWNED_STARCORE_COMPONENTS).issubset(component_ids))

    def test_owned_starcore_component_identity_and_evidence_are_not_generic(self):
        for component_id, hardware_id in OWNED_STARCORE_COMPONENTS.items():
            with self.subTest(component_id=component_id):
                result = self.catalog.get_catalog_record(component_id, project_root=ROOT)
                self.assertTrue(result["success"], result)
                record = result["record"]
                self.assertEqual(record["hardware_id"], hardware_id)
                self.assertTrue(any(any("\u4e00" <= char <= "\u9fff" for char in alias) for alias in record["aliases"]))
                self.assertEqual(record["supported_boards"], [STARCORE_BOARD_ID])
                self.assertEqual(record["verification"]["source_reviewed"]["status"], "verified")
                self.assertEqual(record["verification"]["code_compiled"]["status"], "unverified")
                self.assertEqual(record["verification"]["firmware_uploaded"]["status"], "unverified")
                self.assertEqual(record["verification"]["physical_effect_verified"]["status"], "unverified")
                self.assertEqual(record["historical_lead"]["status"], "legacy_reported")
                self.assertTrue(record["source_ids"])
                self.assertTrue(record["logic_boundary"])
                self.assertIn("extension", record["mindplus"])
                self.assertIn("headers", record["mindplus"])
                self.assertIn("api", record["mindplus"])

    def test_owned_starcore_components_keep_the_three_dangerous_lookalikes_separate(self):
        results = [
            self.catalog.get_catalog_record(component_id, project_root=ROOT)
            for component_id in (
                "idmd-0001-starcore-rgb-light",
                "idms-0001-starcore-button",
                "idms-0009-starcore-ultrasonic",
            )
        ]
        for result in results:
            self.assertTrue(result["success"], result)
        rgb, button, ultrasonic = [result["record"] for result in results]

        self.assertEqual(rgb["interface"], "three-channel-pwm-common-anode")
        self.assertEqual(rgb["mindplus"]["api"], "ledc PWM; LOW increases brightness")
        self.assertNotIn("WS2812", " ".join(rgb["aliases"]))
        self.assertEqual(button["interface"], "three-wire-digital-output")
        self.assertEqual(button["mindplus"]["api"], "pinMode(INPUT); digitalRead(); pressed=HIGH")
        self.assertNotIn("i2c", button["interface"].casefold())
        self.assertEqual(ultrasonic["interface"], "gpio-trigger-echo")
        self.assertEqual(ultrasonic["mindplus"]["extension"], "sen0001")
        self.assertEqual(ultrasonic["mindplus"]["headers"], ["DFRobot_URM10.h"])
        self.assertNotIn("sen0304", ultrasonic["mindplus"]["api"].casefold())

    def test_owned_oled_and_ultrasonic_do_not_reuse_generic_starcore_evidence(self):
        for generic_id in ("ssd1306-i2c-128x64-module", "hc-sr04"):
            with self.subTest(generic_id=generic_id):
                generic = self.catalog.get_catalog_record(generic_id, project_root=ROOT)["record"]
                self.assertNotIn(STARCORE_BOARD_ID, generic["supported_boards"])
                self.assertFalse(any("/starcore/" in path for path in generic["example_files"]))

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
        match_ids = {item["id"] for item in payload["matches"]}
        self.assertIn("linear-potentiometer-10k", match_ids)
        self.assertIn("idms-0003-starcore-potentiometer", match_ids)


if __name__ == "__main__":
    unittest.main()
