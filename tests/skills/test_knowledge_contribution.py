from __future__ import annotations

import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


class KnowledgeContributionContractTests(unittest.TestCase):
    def test_chatmaker_asks_once_only_for_reusable_new_knowledge(self):
        router = (ROOT / "skills" / "chatmaker" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        reference = (
            ROOT
            / "skills"
            / "chatmaker"
            / "references"
            / "beginner-issue-feedback.md"
        ).read_text(encoding="utf-8")

        self.assertIn("successful knowledge contribution", router)
        self.assertIn("ask once", router.casefold())
        self.assertIn("Do not ask after every project", router)
        self.assertIn("改进建议单", router)
        self.assertIn("你不需要懂 GitHub", router)
        self.assertIn("让以后使用的人少走弯路", router)
        self.assertIn("highest evidence state", reference)
        self.assertIn("Never turn an unverified guess into shared knowledge", reference)
        self.assertIn("Amasun93/ChatMaker/issues/new", reference)

    def test_feedback_uses_github_first_and_feishu_without_github(self):
        router = (ROOT / "skills" / "chatmaker" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        reference = (
            ROOT
            / "skills"
            / "chatmaker"
            / "references"
            / "beginner-issue-feedback.md"
        ).read_text(encoding="utf-8")

        self.assertIn("GitHub first", router)
        self.assertIn("chatmaker-feedback --request-json", reference)
        self.assertIn("CHATMAKER_FEEDBACK_FORM_URL", reference)
        self.assertIn("联系邮箱（可选）", reference)
        self.assertIn("show the finished draft", reference)
        self.assertIn("does not need to become a GitHub Issue", reference)

    def test_chatduino_surfaces_new_module_learning_to_chatmaker(self):
        specialist = (ROOT / "skills" / "chatduino" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("knowledge-contribution candidate", specialist)
        self.assertIn("new or previously unsupported module", specialist)
        self.assertIn("Do not publish the Issue from the internal specialist", specialist)

    def test_github_issue_form_collects_reusable_evidence_and_public_consent(self):
        form = yaml.safe_load(
            (
                ROOT
                / ".github"
                / "ISSUE_TEMPLATE"
                / "knowledge-contribution.yml"
            ).read_text(encoding="utf-8")
        )

        fields = {
            item.get("id"): item
            for item in form["body"]
            if isinstance(item, dict) and item.get("id")
        }
        self.assertTrue(
            {
                "project",
                "hardware",
                "knowledge_gap",
                "working_method",
                "evidence_state",
                "privacy_confirmation",
            }.issubset(fields)
        )
        self.assertTrue(fields["privacy_confirmation"]["attributes"]["options"][0]["required"])
        introduction = form["body"][0]["attributes"]["value"]
        self.assertIn("改进建议单", introduction)
        self.assertIn("补充 Skill 和知识库", introduction)
        self.assertIn("帮助后来使用 ChatMaker 的人少走弯路", introduction)


if __name__ == "__main__":
    unittest.main()
