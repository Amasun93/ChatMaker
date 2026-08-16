from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from typing import Any


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
IDENTITY_ERRORS = [
    "invalid_knowledge_request",
    "unknown_knowledge_action",
    "knowledge_board_not_found",
    "knowledge_consumer_not_supported",
    "knowledge_section_not_found",
]


def contract_example(name: str) -> Any:
    text = (ROOT / "docs/contracts/knowledge-api-v1.md").read_text(encoding="utf-8")
    pattern = rf"<!-- contract:{re.escape(name)} -->\s*```json\s*(.*?)\s*```"
    match = re.search(pattern, text, flags=re.DOTALL)
    if match is None:
        raise AssertionError(f"missing JSON contract example: {name}")
    return json.loads(match.group(1))


class KnowledgeApiContractTests(unittest.TestCase):
    def test_section_request_identifies_one_exact_board_section_and_auto_installs(self):
        self.assertEqual(
            contract_example("section.request"),
            {
                "action": "section",
                "board_id": "arduino-nano-classic",
                "consumer": "chatduino",
                "section_id": "start-here",
                "auto_install": True,
            },
        )

    def test_index_success_returns_the_eight_frozen_sections(self):
        response = contract_example("index.success")

        self.assertTrue(response["success"])
        self.assertEqual(response["action"], "index")
        self.assertEqual(
            [section["section_id"] for section in response["sections"]], SECTION_IDS
        )

    def test_section_success_reports_a_complete_utf8_body_with_the_v1_limit(self):
        response = contract_example("section.success")

        self.assertTrue(response["success"])
        self.assertEqual(response["action"], "section")
        self.assertTrue(response["complete"])
        self.assertEqual(response["body_bytes"], len(response["body"].encode("utf-8")))
        self.assertEqual(response["max_body_bytes"], 65_536)
        self.assertLessEqual(response["body_bytes"], response["max_body_bytes"])

    def test_identity_errors_are_knowledge_scoped(self):
        self.assertEqual(contract_example("error.codes")[:5], IDENTITY_ERRORS)

    def test_replacement_leaves_no_legacy_contract_artifacts(self):
        for legacy_path in (
            "docs/contracts/llmwiki-api-v1.md",
            "docs/contributing/llmwiki-format.md",
            "packs/schemas/llmwiki-index.schema.yaml",
        ):
            with self.subTest(legacy_path=legacy_path):
                self.assertFalse((ROOT / legacy_path).exists())


if __name__ == "__main__":
    unittest.main()
