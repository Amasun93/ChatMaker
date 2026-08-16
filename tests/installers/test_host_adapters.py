from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))


class HostAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        from chatmaker.installers.hosts import (  # noqa: PLC0415
            CodexHostAdapter,
            WorkBuddyHostAdapter,
            detect_hosts,
            plan_installation,
        )

        self.CodexHostAdapter = CodexHostAdapter
        self.WorkBuddyHostAdapter = WorkBuddyHostAdapter
        self.detect_hosts = detect_hosts
        self.plan_installation = plan_installation

    @staticmethod
    def report(*, skill_roots=(), mcp_configs=()):
        return {
            "skill_roots": list(skill_roots),
            "mcp_configs": list(mcp_configs),
        }

    def test_explicit_skill_dir_and_mcp_config_take_precedence_for_known_hosts(self):
        report = self.report(
            skill_roots=[
                {"host": "explicit", "path": "D:/chosen/skills", "available": True, "explicit": True},
                {"host": "codex", "path": "C:/Users/teacher/.codex/skills", "available": True, "explicit": False},
                {"host": "workbuddy", "path": "C:/Users/teacher/.workbuddy/skills", "available": True, "explicit": False},
            ],
            mcp_configs=[
                {"host": "explicit", "path": "D:/chosen/mcp.json", "available": True, "explicit": True},
                {"host": "workbuddy", "path": "C:/Users/teacher/.workbuddy/mcp.json", "available": True, "explicit": False},
            ],
        )

        codex_plan = self.CodexHostAdapter().plan({"report": report})
        workbuddy_plan = self.WorkBuddyHostAdapter().plan({"report": report})

        self.assertEqual(codex_plan["skill_dir"], "D:/chosen/skills")
        self.assertEqual(workbuddy_plan["skill_dir"], "D:/chosen/skills")
        self.assertEqual(workbuddy_plan["mcp_config"], "D:/chosen/mcp.json")

    def test_detects_only_existing_codex_and_workbuddy_evidence(self):
        report = self.report(
            skill_roots=[
                {"host": "codex", "path": "C:/Users/teacher/.codex/skills", "available": True, "explicit": False},
                {"host": "workbuddy", "path": "C:/Users/teacher/.workbuddy/skills", "available": False, "explicit": False},
            ],
            mcp_configs=[
                {"host": "workbuddy", "path": "C:/Users/teacher/.workbuddy/mcp.json", "available": True, "explicit": False},
                {"host": "codex", "path": "C:/Users/teacher/.codex/config.toml", "available": False, "explicit": False},
            ],
        )

        detections = self.detect_hosts(report)

        self.assertEqual([item["host"] for item in detections], ["codex", "workbuddy"])
        self.assertTrue(all(item["confidence"] == "high" for item in detections))

    def test_can_detect_codex_and_workbuddy_at_the_same_time(self):
        report = self.report(
            skill_roots=[
                {"host": "codex", "path": "C:/Users/teacher/.codex/skills", "available": True, "explicit": False},
                {"host": "workbuddy", "path": "C:/Users/teacher/.workbuddy/skills", "available": True, "explicit": False},
            ],
            mcp_configs=[],
        )

        result = self.plan_installation({"report": report})

        self.assertEqual(result["status"], "ready")
        self.assertEqual([plan["host"] for plan in result["hosts"]], ["codex", "workbuddy"])

    def test_no_recognized_host_is_ready_with_limits_and_has_no_guessed_writes(self):
        report = self.report(
            skill_roots=[
                {"host": "codex", "path": "C:/Users/teacher/.codex/skills", "available": False, "explicit": False},
                {"host": "workbuddy", "path": "C:/Users/teacher/.workbuddy/skills", "available": False, "explicit": False},
            ],
            mcp_configs=[],
        )

        result = self.plan_installation({"report": report})

        self.assertEqual(result["status"], "ready_with_limits")
        self.assertEqual(result["hosts"], [])
        self.assertEqual(result["writes"], [])
        self.assertNotIn("skill_dir", result)
        self.assertNotIn("mcp_config", result)

    def test_workbuddy_plan_uses_generic_module_entry_and_preserves_other_servers(self):
        report = self.report(
            skill_roots=[
                {"host": "workbuddy", "path": "C:/Users/teacher/.workbuddy/skills", "available": True, "explicit": False},
            ],
            mcp_configs=[
                {"host": "workbuddy", "path": "C:/Users/teacher/.workbuddy/mcp.json", "available": True, "explicit": False},
            ],
        )

        plan = self.WorkBuddyHostAdapter().plan({"report": report})

        self.assertEqual(plan["mcp_server"]["args"], ["-m", "chatmaker.integrations.mcp"])
        self.assertTrue(plan["preserves_unrelated_mcp_servers"])

    def test_workbuddy_installer_keeps_unrelated_mcp_and_registers_generic_module(self):
        from chatmaker.installers import workbuddy  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "mcp.json"
            config.write_text(json.dumps({"mcpServers": {"keep": {"command": "other"}}}), encoding="utf-8")

            installed = workbuddy.install(config, python_executable="python", source_skills=ROOT / "skills")
            saved = json.loads(config.read_text(encoding="utf-8"))

            self.assertTrue(installed["success"])
            self.assertEqual(saved["mcpServers"]["keep"], {"command": "other"})
            self.assertEqual(
                saved["mcpServers"][workbuddy.SERVER_KEY]["args"],
                ["-m", "chatmaker.integrations.mcp"],
            )
            self.assertEqual(
                saved["mcpServers"][workbuddy.SERVER_KEY]["cwd"],
                str((ROOT / "runtime").resolve()),
            )
            workbuddy.uninstall(config)


if __name__ == "__main__":
    unittest.main()
