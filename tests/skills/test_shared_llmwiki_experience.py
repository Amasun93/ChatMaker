import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


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

    def test_chatweb_skill_limits_board_wiki_to_hardware_interfaces_only(self):
        skill = (ROOT / "skills" / "chatweb" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("web-and-protocol", skill)
        self.assertIn("hardware interfaces", skill)
        self.assertIn("Independent classroom tools", skill)
        self.assertIn("do not load board knowledge", skill)
        self.assertNotIn("ChatCAD Skill", skill)


if __name__ == "__main__":
    unittest.main()
