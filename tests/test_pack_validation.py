from __future__ import annotations

import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.packs import validate_repository  # noqa: E402


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

    def test_checked_in_pack_repository_is_valid(self):
        report = self.validate(ROOT / "packs")

        self.assertTrue(report.ok, report.errors)
        self.assertGreaterEqual(report.counts["board"], 3)
        self.assertGreaterEqual(report.counts["component"], 1)
        self.assertGreaterEqual(report.counts["recipe"], 1)


if __name__ == "__main__":
    unittest.main()
