from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.web.planner import CreativeBrief, plan_creative_brief  # noqa: E402


class CreativeBriefPlannerTests(unittest.TestCase):
    def test_vague_brief_asks_at_most_two_plain_questions_and_recommends_no_styles(self):
        result = plan_creative_brief(
            CreativeBrief(kind="classroom-tool", idea="我想做一个课堂网页")
        )

        self.assertEqual(result.status, "clarify")
        self.assertGreaterEqual(len(result.questions), 1)
        self.assertLessEqual(len(result.questions), 2)
        self.assertEqual(result.directions, ())
        self.assertTrue(all(question.endswith("？") for question in result.questions))

    def test_clear_brief_returns_two_or_three_complete_curated_directions(self):
        result = plan_creative_brief(
            CreativeBrief(
                kind="classroom-tool",
                idea="让学生匿名告诉老师哪一步需要重讲",
                audience_scene="初中科学课结束前，全班用手机提交",
                desired_feeling="清醒、安静，不像考试",
                primary_action="学生轻触一次需要重讲按钮",
            )
        )

        self.assertEqual(result.status, "directions")
        self.assertEqual(result.questions, ())
        self.assertGreaterEqual(len(result.directions), 2)
        self.assertLessEqual(len(result.directions), 3)
        self.assertTrue(
            all(
                direction.feeling
                and direction.primary_interaction
                and direction.best_for
                and direction.tradeoff
                for direction in result.directions
            )
        )

    def test_advanced_brief_expands_directions_only_after_explicit_opt_in(self):
        brief = CreativeBrief(
            kind="hardware-interface",
            idea="用手机查看传感器并控制灯",
            audience_scene="学生在展台旁操作本地设备页面",
            core_message="先看清设备状态，再安全控制",
            primary_action="查看状态后按按钮切换灯",
        )

        beginner = plan_creative_brief(brief)
        advanced = plan_creative_brief(brief, advanced=True)

        self.assertLessEqual(len(beginner.directions), 3)
        self.assertGreaterEqual(len(advanced.directions), len(beginner.directions) + 2)
        self.assertFalse(beginner.advanced)
        self.assertTrue(advanced.advanced)


if __name__ == "__main__":
    unittest.main()
