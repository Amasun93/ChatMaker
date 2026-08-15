from __future__ import annotations

import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.packs import canonical_verification_snapshot, validate_repository  # noqa: E402


GATES = {
    "source_reviewed": {
        "status": "verified",
        "checked_at": "2026-08-14",
        "evidence": "Reviewed against the linked manufacturer page.",
    },
    "code_compiled": {"status": "unverified", "checked_at": None, "evidence": None},
    "firmware_uploaded": {"status": "unverified", "checked_at": None, "evidence": None},
    "physical_effect_verified": {
        "status": "unverified",
        "checked_at": None,
        "evidence": None,
    },
}


def write_yaml(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")


def board(record_id: str = "board-one") -> dict:
    return {
        "schema_version": "1.0",
        "kind": "board",
        "id": record_id,
        "name": "Board One",
        "family": "avr",
        "mcu": "ATmega328P",
        "logic_voltage": 5.0,
        "sources": [{"title": "Manufacturer", "url": "https://example.com/board"}],
        "verification": deepcopy(GATES),
        "pins": [
            {"id": "D13", "capabilities": ["digital", "output"]},
            {"id": "GND", "capabilities": ["ground", "shared"]},
        ],
        "constraints": [],
        "toolchains": [{"id": "arduino-cli", "status": "planned"}],
    }


def component(record_id: str = "basic-led") -> dict:
    return {
        "schema_version": "1.0",
        "kind": "component",
        "id": record_id,
        "name": "Basic LED",
        "category": "output",
        "interface": "digital",
        "supply_voltage": {"minimum": 1.8, "maximum": 3.3},
        "sources": [{"title": "Datasheet", "url": "https://example.com/led"}],
        "verification": deepcopy(GATES),
        "pins": [{"id": "anode", "role": "signal"}, {"id": "cathode", "role": "ground"}],
        "supported_boards": ["board-one"],
        "constraints": ["Use a current-limiting resistor."],
        "identification": ["Two leads with a flat edge marking the cathode."],
        "libraries": [],
        "example_files": ["examples/blink/blink.ino"],
        "common_failures": ["Reversed polarity prevents light output."],
        "board_notes": {"board-one": "Use a current-limited digital output."},
    }


def recipe(record_id: str = "blink") -> dict:
    return {
        "schema_version": "1.0",
        "kind": "recipe",
        "id": record_id,
        "name": "Blink",
        "summary": "Blink one LED.",
        "sources": [{"title": "Example", "url": "https://example.com/blink"}],
        "verification": deepcopy(GATES),
        "boards": ["board-one"],
        "components": ["basic-led"],
        "wiring": [
            {"component": "basic-led", "component_pin": "anode", "board_pin": "D13"},
            {"component": "basic-led", "component_pin": "cathode", "board_pin": "GND"},
        ],
        "source_file": "examples/blink/blink.ino",
        "expected_effect": "The LED alternates on and off.",
    }


class PackValidationTests(unittest.TestCase):
    def make_repository(self, root: Path) -> None:
        write_yaml(root / "boards" / "board-one.yaml", board())
        write_yaml(root / "components" / "basic-led.yaml", component())
        write_yaml(root / "recipes" / "blink.yaml", recipe())
        source = root / "examples" / "blink" / "blink.ino"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("void setup() {}\nvoid loop() {}\n", encoding="utf-8")

    def validate(self, root: Path):
        return validate_repository(root, ROOT / "packs" / "schemas")

    def test_valid_repository_reports_record_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)

            report = self.validate(root)

        self.assertTrue(report.ok, report.errors)
        self.assertEqual(report.counts, {"board": 1, "component": 1, "recipe": 1})

    def test_verified_gate_requires_dated_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            invalid = board()
            invalid["verification"]["source_reviewed"] = {
                "status": "verified",
                "checked_at": None,
                "evidence": None,
            }
            write_yaml(root / "boards" / "board-one.yaml", invalid)

            report = self.validate(root)

        self.assertFalse(report.ok)
        self.assertTrue(any("source_reviewed" in error and "evidence" in error for error in report.errors))

    def test_recipe_extension_gate_with_full_gate_shape_is_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            valid = recipe()
            valid["verification"]["wifi_ap_available"] = {
                "status": "verified",
                "checked_at": "2026-08-15",
                "evidence": "Observed the ChatMaker-ESP32 SSID from a phone.",
            }
            valid["verification"]["http_exchange_verified"] = {
                "status": "unverified",
                "checked_at": None,
                "evidence": None,
            }
            write_yaml(root / "recipes" / "blink.yaml", valid)

            report = self.validate(root)

        self.assertTrue(report.ok, report.errors)

    def test_recipe_extension_gate_must_use_the_same_gate_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            invalid = recipe()
            invalid["verification"]["wifi_ap_available"] = {"status": "pending"}
            write_yaml(root / "recipes" / "blink.yaml", invalid)

            report = self.validate(root)

        self.assertFalse(report.ok)
        self.assertTrue(any("wifi_ap_available" in error for error in report.errors), report.errors)

    def test_duplicate_ids_fail_even_across_record_kinds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            duplicate = component(record_id="board-one")
            duplicate["supported_boards"] = ["board-one"]
            write_yaml(root / "components" / "duplicate.yaml", duplicate)

            report = self.validate(root)

        self.assertFalse(report.ok)
        self.assertTrue(any("duplicate id 'board-one'" in error for error in report.errors))

    def test_unknown_board_and_component_references_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            invalid = recipe()
            invalid["boards"] = ["missing-board"]
            invalid["components"] = ["missing-component"]
            write_yaml(root / "recipes" / "blink.yaml", invalid)

            report = self.validate(root)

        self.assertFalse(report.ok)
        self.assertTrue(any("unknown board 'missing-board'" in error for error in report.errors))
        self.assertTrue(any("unknown component 'missing-component'" in error for error in report.errors))

    def test_pin_conflict_fails_unless_the_connection_is_shared(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            conflict = recipe()
            conflict["wiring"].append(
                {"component": "basic-led", "component_pin": "cathode", "board_pin": "D13"}
            )
            write_yaml(root / "recipes" / "blink.yaml", conflict)

            report = self.validate(root)

        self.assertFalse(report.ok)
        self.assertTrue(any("board pin 'D13'" in error and "conflict" in error for error in report.errors))

    def test_missing_recipe_source_file_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            (root / "examples" / "blink" / "blink.ino").unlink()

            report = self.validate(root)

        self.assertFalse(report.ok)
        self.assertTrue(any("source_file" in error and "does not exist" in error for error in report.errors))

    def test_missing_component_example_file_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            invalid = component()
            invalid["example_files"] = ["examples/missing/missing.ino"]
            write_yaml(root / "components" / "basic-led.yaml", invalid)

            report = self.validate(root)

        self.assertFalse(report.ok)
        self.assertTrue(any("example_file" in error and "does not exist" in error for error in report.errors))

    def test_unknown_component_and_board_pins_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            invalid = recipe()
            invalid["wiring"] = [
                {"component": "basic-led", "component_pin": "mystery", "board_pin": "D12"}
            ]
            write_yaml(root / "recipes" / "blink.yaml", invalid)

            report = self.validate(root)

        self.assertFalse(report.ok)
        self.assertTrue(any("component pin 'mystery'" in error for error in report.errors))
        self.assertTrue(any("board pin 'D12'" in error for error in report.errors))

    def test_component_learning_fields_are_required(self):
        required_learning_fields = (
            "identification",
            "libraries",
            "example_files",
            "common_failures",
            "board_notes",
        )
        for field in required_learning_fields:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_repository(root)
                invalid = component()
                invalid.pop(field)
                write_yaml(root / "components" / "basic-led.yaml", invalid)

                report = self.validate(root)

                self.assertFalse(report.ok)
                self.assertTrue(any(field in error for error in report.errors), report.errors)

    def test_checked_in_pack_repository_is_valid(self):
        report = self.validate(ROOT / "packs")

        self.assertTrue(report.ok, report.errors)
        self.assertGreaterEqual(report.counts["board"], 3)
        self.assertGreaterEqual(report.counts["component"], 1)
        self.assertGreaterEqual(report.counts["recipe"], 1)

    def test_first_component_pack_contains_the_planned_twelve_modules(self):
        expected_ids = {
            "basic-led",
            "common-cathode-rgb-led",
            "momentary-button-two-pin",
            "analog-light-sensor-module",
            "active-buzzer-module",
            "hc-sr04",
            "dht11-three-pin-module",
            "sg90-micro-servo",
            "ssd1306-i2c-128x64-module",
            "one-channel-relay-module-5v",
            "linear-potentiometer-10k",
            "ws2812b-addressable-rgb",
        }
        component_ids = {
            yaml.safe_load(path.read_text(encoding="utf-8"))["id"]
            for path in sorted((ROOT / "packs" / "components").glob("*.yaml"))
        }

        self.assertTrue(expected_ids.issubset(component_ids), expected_ids - component_ids)

    def test_migrated_nano_examples_have_recipe_records(self):
        expected_source_files = {
            "examples/chatduino/nano/blink/blink.ino",
            "examples/chatduino/nano/dht11-serial/dht11-serial.ino",
            "examples/chatduino/nano/light-led/light-led.ino",
            "examples/chatduino/nano/oled-light/oled-light.ino",
            "examples/chatduino/nano/servo-button/servo-button.ino",
            "examples/chatduino/nano/ultrasonic-buzzer/ultrasonic-buzzer.ino",
        }
        recipes = [
            yaml.safe_load(path.read_text(encoding="utf-8"))
            for path in sorted((ROOT / "packs" / "recipes").glob("*.yaml"))
        ]

        actual_source_files = {record["source_file"] for record in recipes}

        self.assertTrue(
            expected_source_files.issubset(actual_source_files),
            expected_source_files - actual_source_files,
        )

    def test_uno_blink_has_a_dedicated_recipe_and_source_file(self):
        recipes = [
            yaml.safe_load(path.read_text(encoding="utf-8"))
            for path in sorted((ROOT / "packs" / "recipes").glob("*.yaml"))
        ]
        matches = [record for record in recipes if record["id"] == "uno-blink-built-in"]

        self.assertEqual(len(matches), 1, "Uno Blink recipe is missing")
        self.assertEqual(matches[0]["boards"], ["arduino-uno-r3"])
        self.assertEqual(
            matches[0]["source_file"],
            "examples/chatduino/uno/blink/blink.ino",
        )
        self.assertTrue((ROOT / matches[0]["source_file"]).is_file())

    def test_esp32_board_record_keeps_module_and_carrier_identity_separate(self):
        record = yaml.safe_load(
            (ROOT / "packs" / "boards" / "esp32-devkit-v1.yaml").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(record["name"], "DOIT ESP32 DEVKIT V1 (ESP-WROOM-32)")
        self.assertEqual(
            record["identity"]["profile_id"],
            "doit-esp32-devkit-v1-wroom32",
        )
        self.assertEqual(record["identity"]["carrier_board"], "DOIT ESP32 DEVKIT V1")
        self.assertEqual(record["identity"]["module"], "ESP-WROOM-32")
        self.assertTrue(record["identity"]["physical_confirmation_required"])
        self.assertEqual(
            record["identity"]["allowed_fqbn"],
            ["esp32:esp32:esp32doit-devkit-v1"],
        )
        self.assertIn("FireBeetle", record["identity"]["forbidden_aliases"])
        self.assertIn("GPIO23", {pin["id"] for pin in record["pins"]})
        self.assertIn("3V3", {pin["id"] for pin in record["pins"]})

    def test_esp32_external_led_recipe_avoids_boot_strapping_pin(self):
        record = yaml.safe_load(
            (ROOT / "packs" / "recipes" / "esp32-external-led-blink.yaml").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(record["boards"], ["esp32-devkit-v1"])
        self.assertEqual(record["components"], ["basic-led"])
        self.assertEqual(
            record["source_file"],
            "examples/chatduino/esp32/blink-external-led/blink-external-led.ino",
        )
        self.assertEqual(record["verification"]["code_compiled"]["status"], "unverified")
        signal_pins = {
            item["board_pin"] for item in record["wiring"] if item["component_pin"] == "anode"
        }
        self.assertEqual(signal_pins, {"GPIO23"})
        self.assertTrue((ROOT / record["source_file"]).is_file())

    def test_canonical_verification_snapshot_ignores_llmwiki_sidecars(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            llmwiki = root / "llmwiki" / "boards" / "board-one.yaml"
            llmwiki.parent.mkdir(parents=True, exist_ok=True)
            llmwiki.write_text(
                "schema_version: '1.0'\nkind: llmwiki-index\nboard_id: board-one\n",
                encoding="utf-8",
            )

            snapshot, digest = canonical_verification_snapshot(root)

        self.assertEqual(len(snapshot), 3)
        self.assertEqual([item["kind"] for item in snapshot], ["board", "component", "recipe"])
        self.assertEqual(len(digest), 64)


if __name__ == "__main__":
    unittest.main()
