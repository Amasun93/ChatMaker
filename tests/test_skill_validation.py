from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.skills import validate_skill_directory  # noqa: E402


class SkillValidationTests(unittest.TestCase):
    def test_minimal_skill_with_ui_metadata_is_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            skill = Path(directory) / "sample-skill"
            (skill / "agents").mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nname: sample-skill\ndescription: Use this sample for a concrete workflow.\n---\n\n# Sample\n\nDo the work.\n",
                encoding="utf-8",
            )
            (skill / "agents" / "openai.yaml").write_text(
                "interface:\n"
                '  display_name: "Sample Skill"\n'
                '  short_description: "Run a concrete sample workflow safely"\n'
                '  default_prompt: "Use $sample-skill to complete this sample workflow."\n',
                encoding="utf-8",
            )

            errors = validate_skill_directory(skill)

        self.assertEqual(errors, [])

    def test_extra_frontmatter_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            skill = Path(directory) / "sample-skill"
            (skill / "agents").mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nname: sample-skill\ndescription: Valid description.\nversion: 1.0\n---\n\n# Sample\n",
                encoding="utf-8",
            )
            (skill / "agents" / "openai.yaml").write_text(
                "interface:\n"
                '  display_name: "Sample Skill"\n'
                '  short_description: "Run a concrete sample workflow safely"\n'
                '  default_prompt: "Use $sample-skill to complete this sample workflow."\n',
                encoding="utf-8",
            )

            errors = validate_skill_directory(skill)

        self.assertTrue(any("frontmatter keys" in error for error in errors))

    def test_default_prompt_must_name_the_skill(self):
        with tempfile.TemporaryDirectory() as directory:
            skill = Path(directory) / "sample-skill"
            (skill / "agents").mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nname: sample-skill\ndescription: Valid description.\n---\n\n# Sample\n",
                encoding="utf-8",
            )
            (skill / "agents" / "openai.yaml").write_text(
                "interface:\n"
                '  display_name: "Sample Skill"\n'
                '  short_description: "Run a concrete sample workflow safely"\n'
                '  default_prompt: "Complete this sample workflow."\n',
                encoding="utf-8",
            )

            errors = validate_skill_directory(skill)

        self.assertTrue(any("$sample-skill" in error for error in errors))

    def test_checked_in_skills_are_valid(self):
        skill_dirs = sorted(path for path in (ROOT / "skills").iterdir() if path.is_dir())

        self.assertEqual([path.name for path in skill_dirs], ["chatduino", "chatmaker", "chatmaker-web"])
        for skill in skill_dirs:
            with self.subTest(skill=skill.name):
                self.assertEqual(validate_skill_directory(skill), [])


if __name__ == "__main__":
    unittest.main()

