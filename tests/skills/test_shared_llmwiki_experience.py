import unittest
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.route import chatweb_llmwiki_requests_for_intent  # noqa: E402


class SharedLlmWikiExperienceTests(unittest.TestCase):
    def test_chatmaker_skill_reads_start_index_after_exact_board_identity(self):
        skill = (ROOT / "skills" / "chatmaker" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("exact board identity", skill)
        self.assertIn("start-here", skill)
        self.assertIn("llmwiki_get", skill)

    def test_chatduino_skill_reads_safety_pins_toolchain_and_canonical_facts(self):
        skill = (ROOT / "skills" / "chatduino" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("identify-and-safety", skill)
        self.assertIn("pins-and-electrical", skill)
        self.assertIn("toolchains-and-upload", skill)
        self.assertIn("canonical facts", skill)

    def test_chatweb_skill_documents_hardware_only_board_wiki_boundary(self):
        skill = (ROOT / "skills" / "chatweb" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("web-and-protocol", skill)
        self.assertIn("hardware interfaces", skill)
        self.assertIn("Independent classroom tools", skill)
        self.assertIn("do not load board knowledge", skill)
        self.assertNotIn("ChatCAD Skill", skill)

    def test_independent_web_work_does_not_plan_any_llmwiki_board_request(self):
        requests = chatweb_llmwiki_requests_for_intent(
            {
                "web": {
                    "outcome": "classroom pulse board",
                    "audience": "students",
                }
            },
            board_id="arduino-nano-classic",
        )

        self.assertEqual(requests, [])

    def test_hardware_interface_web_work_plans_only_web_and_protocol_section(self):
        requests = chatweb_llmwiki_requests_for_intent(
            {
                "hardware": {"board": "arduino-nano-classic", "outcome": "sensor console"},
                "web": {"outcome": "phone control panel"},
                "communication_contract": {
                    "transport": "HTTP",
                    "interactions": [
                        {"request": "GET /api/state", "response": "JSON state"}
                    ],
                },
            },
            board_id="arduino-nano-classic",
        )

        self.assertEqual(
            requests,
            [
                {
                    "action": "section",
                    "board_id": "arduino-nano-classic",
                    "consumer": "chatweb",
                    "section_id": "web-and-protocol",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
