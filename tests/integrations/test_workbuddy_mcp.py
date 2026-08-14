import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load(name, relative):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class WorkBuddyBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = load(
            "chatmaker_workbuddy_mcp",
            "runtime/chatmaker/integrations/workbuddy_mcp.py",
        )
        cls.installer = load(
            "chatmaker_workbuddy_installer",
            "runtime/chatmaker/installers/workbuddy.py",
        )

    def test_server_exposes_nano_tools_only(self):
        names = {tool["name"] for tool in self.server.TOOLS}

        self.assertEqual(
            names,
            {
                "nano_prepare_environment",
                "nano_doctor",
                "nano_ports",
                "nano_compile",
                "nano_compile_upload",
            },
        )
        self.assertFalse(any("starcore" in name for name in names))
        upload_tool = next(
            tool for tool in self.server.TOOLS
            if tool["name"] == "nano_compile_upload"
        )
        self.assertIn("自动", upload_tool["description"])
        self.assertIn("接入", upload_tool["description"])

    def test_stdio_server_answers_ping_in_a_real_subprocess(self):
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(ROOT / "runtime")
        completed = subprocess.run(
            [sys.executable, str(ROOT / "runtime/chatmaker/integrations/workbuddy_mcp.py")],
            input='{"jsonrpc":"2.0","id":1,"method":"ping"}\n',
            text=True,
            capture_output=True,
            cwd=ROOT,
            env=environment,
            timeout=10,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        response = json.loads(completed.stdout)
        self.assertEqual(response, {"jsonrpc": "2.0", "id": 1, "result": {}})

    def test_installer_preserves_existing_servers(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "mcp.json"
            config.write_text(
                json.dumps({"mcpServers": {"existing": {"command": "keep-me"}}}),
                encoding="utf-8",
            )

            result = self.installer.install(config, python_executable="python")
            saved = json.loads(config.read_text(encoding="utf-8"))

            self.assertTrue(result["success"])
            self.assertEqual(saved["mcpServers"]["existing"]["command"], "keep-me")
            self.assertIn("arduino-nano-mindplus", saved["mcpServers"])
            self.assertIsNotNone(result["backup"])

    def test_waiting_for_hardware_is_a_prompt_not_an_mcp_tool_error(self):
        original = self.server.bridge.execute_request
        self.server.bridge.execute_request = lambda request: {
            "success": False,
            "stage": "awaiting-hardware",
            "hardware_connection_required": True,
            "teacher_message": "请接入 Nano，接入后自动上传。",
        }
        try:
            result = self.server._tool_result(
                "nano_compile_upload", {"code": "void setup(){} void loop(){}"}
            )
        finally:
            self.server.bridge.execute_request = original

        self.assertFalse(result["isError"])

    def test_install_and_uninstall_restore_config_and_existing_skill(self):
        with tempfile.TemporaryDirectory() as temporary:
            workbuddy_home = Path(temporary) / ".workbuddy"
            config = workbuddy_home / "mcp.json"
            config.parent.mkdir(parents=True)
            original = {"mcpServers": {"existing": {"command": "keep-me"}}}
            config.write_text(json.dumps(original), encoding="utf-8")
            old_chatweb = workbuddy_home / "skills" / "chatweb"
            old_chatweb.mkdir(parents=True)
            (old_chatweb / "old-marker.txt").write_text("restore me", encoding="utf-8")

            try:
                installed = self.installer.install(
                    config,
                    python_executable="python",
                    source_skills=ROOT / "skills",
                )
            except TypeError as exc:
                self.fail(f"WorkBuddy installer does not support Skill installation: {exc}")

            self.assertTrue(installed["success"])
            self.assertTrue((workbuddy_home / "skills" / "chatmaker" / "SKILL.md").is_file())
            self.assertTrue(Path(installed["manifest"]).is_file())

            removed = self.installer.uninstall(config)
            restored_config = json.loads(config.read_text(encoding="utf-8"))

            self.assertTrue(removed["success"])
            self.assertEqual(restored_config, original)
            self.assertEqual(
                (old_chatweb / "old-marker.txt").read_text(encoding="utf-8"),
                "restore me",
            )
            self.assertFalse((workbuddy_home / "skills" / "chatmaker").exists())


if __name__ == "__main__":
    unittest.main()
