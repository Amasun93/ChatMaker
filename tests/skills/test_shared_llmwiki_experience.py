import unittest
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.route import execute_request  # noqa: E402


class SharedLlmWikiExperienceTests(unittest.TestCase):
    def test_chatmaker_skill_reads_start_index_after_exact_board_identity(self):
        skill = (ROOT / "skills" / "chatmaker" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("exact board identity", skill)
        self.assertIn("start-here", skill)
        self.assertIn("llmwiki_get", skill)
        self.assertIn("WorkBuddy", skill)
        self.assertIn("chatmaker-llmwiki --request-json", skill)
        self.assertIn("Codex", skill)

    def test_chatduino_skill_reads_safety_pins_toolchain_and_canonical_facts(self):
        skill = (ROOT / "skills" / "chatduino" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("identify-and-safety", skill)
        self.assertIn("pins-and-electrical", skill)
        self.assertIn("toolchains-and-upload", skill)
        self.assertIn("canonical facts", skill)
        self.assertIn("WorkBuddy", skill)
        self.assertIn("llmwiki_get", skill)
        self.assertIn("chatmaker-llmwiki --request-json", skill)
        self.assertIn("Codex", skill)

    def test_chatweb_skill_documents_hardware_only_board_wiki_boundary(self):
        skill = (ROOT / "skills" / "chatweb" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("web-and-protocol", skill)
        self.assertIn("hardware interfaces", skill)
        self.assertIn("Independent classroom tools", skill)
        self.assertIn("do not load board knowledge", skill)
        self.assertNotIn("ChatCAD Skill", skill)

    def test_independent_web_work_does_not_plan_any_llmwiki_board_request(self):
        result = execute_request(
            {
                "web": {
                    "outcome": "classroom pulse board",
                    "audience": "students",
                }
            },
        )

        self.assertTrue(result["success"], result)
        self.assertEqual(result["route"], "web")
        self.assertEqual(result["llmwiki_requests"], [])

    def test_hardware_interface_web_work_plans_only_web_and_protocol_section(self):
        result = execute_request(
            {
                "hardware": {"board": "arduino-nano-classic", "outcome": "sensor console"},
                "web": {"outcome": "phone control panel"},
                "communication_contract": {
                    "transport": "HTTP",
                    "interactions": [
                        {"request": "GET /api/state", "response": "JSON state"}
                    ],
                },
            }
        )

        self.assertEqual(
            result["llmwiki_requests"],
            [
                {
                    "action": "section",
                    "board_id": "arduino-nano-classic",
                    "consumer": "chatweb",
                    "section_id": "web-and-protocol",
                }
            ],
        )

    def test_malformed_board_identity_does_not_trigger_a_board_request(self):
        result = execute_request(
            {
                "hardware": {"board": "arduino-nano-classic-typo", "outcome": "sensor console"},
                "web": {"outcome": "phone control panel"},
                "communication_contract": {
                    "transport": "HTTP",
                    "interactions": [
                        {"request": "GET /api/state", "response": "JSON state"}
                    ],
                },
            }
        )

        self.assertTrue(result["success"], result)
        self.assertEqual(result["route"], "combined")
        self.assertEqual(result["llmwiki_requests"], [])


if __name__ == "__main__":
    unittest.main()
