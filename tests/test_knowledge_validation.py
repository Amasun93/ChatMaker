from __future__ import annotations

import unittest
from copy import deepcopy
from pathlib import Path

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[1]
SECTION_IDS = [
    "start-here",
    "identify-and-safety",
    "pins-and-electrical",
    "toolchains-and-upload",
    "components-and-wiring",
    "libraries-and-examples",
    "web-and-protocol",
    "troubleshooting",
]


class KnowledgeIndexValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = yaml.safe_load(
            (ROOT / "packs/schemas/knowledge-index.schema.yaml").read_text(encoding="utf-8")
        )
        cls.validator = jsonschema.Draft202012Validator(cls.schema)

    def valid_index(self) -> dict:
        return {
            "schema_version": "1.0",
            "kind": "knowledge-index",
            "board_id": "arduino-nano-classic",
            "max_section_bytes": 65_536,
            "sections": [
                {
                    "section_id": section_id,
                    "title": section_id.replace("-", " ").title(),
                    "summary": f"Bounded knowledge for {section_id}.",
                    "consumers": ["chatmaker", "chatduino", "chatweb"],
                    "topics": [section_id],
                    "pack_id": "chatmaker-board-arduino-nano-classic-knowledge",
                }
                for section_id in SECTION_IDS
            ],
        }

    def test_schema_accepts_one_complete_knowledge_index(self):
        index = self.valid_index()

        self.validator.validate(index)

    def test_schema_rejects_a_non_v1_body_limit(self):
        index = self.valid_index()
        index["max_section_bytes"] = 65_537

        with self.assertRaises(jsonschema.ValidationError):
            self.validator.validate(index)

    def test_schema_rejects_a_missing_required_section(self):
        index = self.valid_index()
        index["sections"] = [
            section for section in index["sections"] if section["section_id"] != "start-here"
        ]

        with self.assertRaises(jsonschema.ValidationError):
            self.validator.validate(index)

    def test_schema_rejects_an_extra_section(self):
        index = self.valid_index()
        extra = deepcopy(index["sections"][0])
        extra["section_id"] = "unexpected-section"
        extra["topics"] = ["unexpected-section"]
        index["sections"].append(extra)

        with self.assertRaises(jsonschema.ValidationError):
            self.validator.validate(index)


if __name__ == "__main__":
    unittest.main()
