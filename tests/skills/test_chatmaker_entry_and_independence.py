from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))


class ChatMakerEntryAndIndependenceTests(unittest.TestCase):
    def test_chatmaker_is_the_only_user_facing_skill_entry(self):
        skills = ROOT / "skills"
        self.assertEqual(
            {path.name for path in skills.iterdir() if path.is_dir()},
            {"chatmaker", "chatduino", "chatweb", "chatcad"},
        )
        self.assertTrue((skills / "chatmaker" / "agents" / "openai.yaml").is_file())
        for name in ("chatduino", "chatweb", "chatcad"):
            with self.subTest(skill=name):
                self.assertFalse((skills / name / "agents" / "openai.yaml").exists())

    def test_router_names_every_internal_specialist_and_each_names_its_parent(self):
        router = (ROOT / "skills" / "chatmaker" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("only user entry", router)
        for name in ("chatduino", "chatweb", "chatcad"):
            self.assertIn(f"${name}", router)
            specialist = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("internal specialist", specialist)
            self.assertIn("ChatMaker", specialist)

    def test_runtime_and_skills_do_not_reference_external_legacy_skill_roots(self):
        forbidden = (
            re.compile(r"starcore-project-maker", re.IGNORECASE),
            re.compile(r"(?:\.codex|\.agents)[/\\\\]skills[/\\\\](?:arduino-nano-mindplus|starcore|unihiker)", re.IGNORECASE),
            re.compile(r"[A-Za-z]:[/\\\\].*[/\\\\](?:arduino-nano-mindplus|starcore-project-maker|unihiker)[/\\\\]", re.IGNORECASE),
        )
        for root in (ROOT / "runtime", ROOT / "skills"):
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix not in {".py", ".md", ".yaml", ".yml", ".json"}:
                    continue
                text = path.read_text(encoding="utf-8")
                with self.subTest(path=path.relative_to(ROOT)):
                    self.assertFalse(any(pattern.search(text) for pattern in forbidden))

    def test_readme_install_prompts_start_at_chatmaker(self):
        chinese = (ROOT / "README.md").read_text(encoding="utf-8")
        english = (ROOT / "README_EN.md").read_text(encoding="utf-8")
        self.assertIn("唯一入口", chinese)
        self.assertIn("使用 $chatmaker", chinese)
        self.assertIn("only user entry", english)
        self.assertIn("Use $chatmaker", english)


if __name__ == "__main__":
    unittest.main()
