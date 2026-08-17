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

    def test_server_exposes_hardware_knowledge_serial_and_cad_tools(self):
        names = {tool["name"] for tool in self.server.TOOLS}

        self.assertEqual(
            names,
            {
                "nano_prepare_environment",
                "nano_doctor",
                "nano_ports",
                "nano_compile",
                "nano_compile_upload",
                "uno_prepare_environment",
                "uno_doctor",
                "uno_ports",
                "uno_compile",
                "uno_compile_upload",
                "avr_project_run",
                "starcore_doctor",
                "starcore_ports",
                "starcore_compile",
                "starcore_compile_upload",
                "esp32_prepare_environment",
                "esp32_doctor",
                "esp32_ports",
                "esp32_compile",
                "esp32_compile_upload",
                "serial_list",
                "serial_open",
                "serial_read",
                "serial_expect",
                "serial_write",
                "serial_close",
                "catalog_search",
                "catalog_get",
                "knowledge_get",
                "cad_profile_get",
                "cad_fabrication_get",
                "cad_generate",
            },
        )
        self.assertEqual(self.server.SERVER_VERSION, "1.13.0")
        self.assertEqual(len(names), 32)
        upload_tool = next(
            tool for tool in self.server.TOOLS
            if tool["name"] == "nano_compile_upload"
        )
        self.assertIn("自动", upload_tool["description"])
        self.assertIn("接入", upload_tool["description"])

    def test_avr_project_run_routes_to_continuous_flow(self):
        captured = None
        original = self.server.project_flow.run_project
        original_suspend = self.server.serial_monitor.SERIAL_MANAGER.suspend_all
        original_resume = self.server.serial_monitor.SERIAL_MANAGER.resume_all

        def fake(request, **options):
            nonlocal captured
            captured = request
            return {"success": False, "state": "compiled-awaiting-hardware"}

        self.server.project_flow.run_project = fake
        self.server.serial_monitor.SERIAL_MANAGER.suspend_all = lambda: []
        self.server.serial_monitor.SERIAL_MANAGER.resume_all = lambda sessions: []
        try:
            result = self.server._tool_result(
                "avr_project_run",
                {"board_id": "arduino-uno-r3", "code": "void setup(){} void loop(){}"},
            )
        finally:
            self.server.project_flow.run_project = original
            self.server.serial_monitor.SERIAL_MANAGER.suspend_all = original_suspend
            self.server.serial_monitor.SERIAL_MANAGER.resume_all = original_resume

        self.assertFalse(result["isError"])
        self.assertEqual(captured["board_id"], "arduino-uno-r3")

    def test_initialize_routes_esp32_to_safe_compile_upload(self):
        response = self.server.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05"},
            }
        )

        instructions = response["result"]["instructions"]
        self.assertIn("catalog_search/get", instructions)
        self.assertIn("esp32_compile_upload", instructions)
        self.assertIn("唯一非蓝牙有线端口", instructions)
        self.assertIn("HTTP", instructions)
        self.assertIn("knowledge_get", instructions)
        self.assertIn("start-here", instructions)
        self.assertIn("avr_project_run", instructions)
        self.assertIn("星核板", instructions)

    def test_knowledge_get_routes_index_or_section_to_shared_reader(self):
        original = self.server.knowledge.execute_request
        captured = []

        def fake(request):
            captured.append(request)
            return {"success": True, "action": request["action"]}

        self.server.knowledge.execute_request = fake
        try:
            index = self.server._tool_result(
                "knowledge_get",
                {"board_id": "arduino-nano-classic", "consumer": "chatmaker"},
            )
            section = self.server._tool_result(
                "knowledge_get",
                {
                    "board_id": "arduino-nano-classic",
                    "consumer": "chatduino",
                    "section_id": "identify-and-safety",
                    "auto_install": False,
                },
            )
        finally:
            self.server.knowledge.execute_request = original

        self.assertFalse(index["isError"])
        self.assertFalse(section["isError"])
        self.assertEqual(
            captured,
            [
                {
                    "action": "index",
                    "board_id": "arduino-nano-classic",
                    "consumer": "chatmaker",
                },
                {
                    "action": "section",
                    "board_id": "arduino-nano-classic",
                    "consumer": "chatduino",
                    "section_id": "identify-and-safety",
                    "auto_install": False,
                },
            ],
        )

    def test_esp32_prepare_environment_routes_to_locked_auto_prepare(self):
        """Catches the MCP tool falling back to read-only doctor instead of preparation."""
        tool = next(
            tool for tool in self.server.TOOLS
            if tool["name"] == "esp32_prepare_environment"
        )
        self.assertIn("自动检查", tool["description"])
        self.assertIn("ChatMaker 验证", tool["description"])
        captured = None
        original = self.server.esp32_bridge.execute_request

        def fake(request):
            nonlocal captured
            captured = request
            return {"success": True, "action": "prepare-environment"}

        self.server.esp32_bridge.execute_request = fake
        try:
            result = self.server._tool_result("esp32_prepare_environment", {})
        finally:
            self.server.esp32_bridge.execute_request = original

        self.assertFalse(result["isError"])
        self.assertEqual(captured, {"action": "prepare-environment"})

    def test_esp32_toolchain_missing_is_a_prompt_not_an_mcp_error(self):
        original = self.server.esp32_bridge.execute_request
        self.server.esp32_bridge.execute_request = lambda request: {
            "success": False,
            "error": "exact_esp32_toolchain_missing",
            "ready_for_compile": False,
            "installation_performed": False,
            "required_fqbn": "esp32:esp32:esp32doit-devkit-v1",
        }
        try:
            result = self.server._tool_result("esp32_doctor", {})
        finally:
            self.server.esp32_bridge.execute_request = original

        self.assertFalse(result["isError"])
        payload = json.loads(result["content"][0]["text"])
        self.assertEqual(payload["error"], "exact_esp32_toolchain_missing")

    def test_esp32_compile_routes_code_with_explicit_board_profile(self):
        captured = None
        original = self.server.esp32_bridge.execute_request

        def fake(request):
            nonlocal captured
            captured = request
            return {"success": True, "action": "compile"}

        self.server.esp32_bridge.execute_request = fake
        try:
            result = self.server._tool_result(
                "esp32_compile",
                {
                    "code": "void setup(){} void loop(){}",
                    "board_profile": "doit-esp32-devkit-v1-wroom32",
                },
            )
        finally:
            self.server.esp32_bridge.execute_request = original

        self.assertFalse(result["isError"])
        self.assertEqual(captured["action"], "compile")
        self.assertEqual(
            captured["board_profile"], "doit-esp32-devkit-v1-wroom32"
        )

    def test_esp32_tool_schemas_publish_the_runtime_compile_timeout_policy(self):
        """Catches AI hosts reintroducing the old compile budget via schema defaults."""
        tools = {tool["name"]: tool for tool in self.server.TOOLS}

        compile_properties = tools["esp32_compile"]["inputSchema"]["properties"]
        upload_properties = tools["esp32_compile_upload"]["inputSchema"]["properties"]

        self.assertEqual(compile_properties["timeout"]["default"], 1200)
        self.assertEqual(upload_properties["timeout"]["default"], 1200)
        self.assertEqual(upload_properties["upload_timeout"]["default"], 300)

    def test_esp32_waiting_for_hardware_is_not_an_mcp_tool_error(self):
        original = self.server.esp32_bridge.execute_request
        self.server.esp32_bridge.execute_request = lambda request: {
            "success": False,
            "stage": "awaiting-hardware",
            "hardware_connection_required": True,
            "teacher_message": "请接入已确认的 DOIT ESP32 DevKit V1。",
        }
        try:
            result = self.server._tool_result(
                "esp32_compile_upload",
                {
                    "code": "void setup(){} void loop(){}",
                    "board_profile": "doit-esp32-devkit-v1-wroom32",
                },
            )
        finally:
            self.server.esp32_bridge.execute_request = original

        self.assertFalse(result["isError"])
        payload = json.loads(result["content"][0]["text"])
        self.assertEqual(payload["stage"], "awaiting-hardware")

    def test_catalog_tools_read_the_real_component_pack(self):
        self.assertIn("catalog_search", {tool["name"] for tool in self.server.TOOLS})
        result = self.server._tool_result(
            "catalog_search", {"query": "继电器", "kind": "component"}
        )

        payload = json.loads(result["content"][0]["text"])
        self.assertFalse(result["isError"])
        self.assertTrue(payload["success"], payload)
        self.assertEqual(payload["matches"][0]["id"], "one-channel-relay-module-5v")

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

            result = self.installer.install(
                config,
                python_executable="python",
                transaction_root=Path(temporary) / "global-chatmaker-state",
            )
            saved = json.loads(config.read_text(encoding="utf-8"))

            self.assertTrue(result["success"])
            self.assertEqual(saved["mcpServers"]["existing"]["command"], "keep-me")
            self.assertIn(self.installer.SERVER_KEY, saved["mcpServers"])
            self.assertEqual(self.installer.SERVER_KEY, "chatmaker")
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

    def test_uno_waiting_for_hardware_is_a_prompt_not_an_mcp_tool_error(self):
        self.assertIn("uno_compile_upload", {tool["name"] for tool in self.server.TOOLS})
        original = self.server.uno_bridge.execute_request
        self.server.uno_bridge.execute_request = lambda request: {
            "success": False,
            "stage": "awaiting-hardware",
            "hardware_connection_required": True,
            "teacher_message": "请接入 Uno，接入后自动上传。",
        }
        try:
            result = self.server._tool_result(
                "uno_compile_upload", {"code": "void setup(){} void loop(){}"}
            )
        finally:
            self.server.uno_bridge.execute_request = original

        self.assertFalse(result["isError"])
        payload = json.loads(result["content"][0]["text"])
        self.assertEqual(payload["stage"], "awaiting-hardware")

    def test_compile_upload_suspends_and_resumes_serial_sessions(self):
        class FakeSerialManager:
            def __init__(self):
                self.suspended = False
                self.resumed = None

            def suspend_all(self):
                self.suspended = True
                return [{"port": "COM9", "baudrate": 9600, "timeout": 0.1}]

            def resume_all(self, settings):
                self.resumed = settings
                return [{"success": True, "session_id": "serial-COM9-restored"}]

        manager = FakeSerialManager()
        original_manager = self.server.serial_monitor.SERIAL_MANAGER
        original_execute = self.server.bridge.execute_request
        self.server.serial_monitor.SERIAL_MANAGER = manager
        self.server.bridge.execute_request = lambda request: {
            "success": True,
            "stage": "complete",
        }
        try:
            result = self.server._tool_result(
                "nano_compile_upload",
                {"code": "void setup(){} void loop(){}"},
            )
        finally:
            self.server.serial_monitor.SERIAL_MANAGER = original_manager
            self.server.bridge.execute_request = original_execute

        payload = json.loads(result["content"][0]["text"])
        self.assertTrue(manager.suspended)
        self.assertEqual(manager.resumed[0]["port"], "COM9")
        self.assertTrue(payload["serial_sessions"]["closed_before_upload"])
        self.assertTrue(payload["serial_sessions"]["reopened_after_upload"][0]["success"])

    def test_install_and_uninstall_restore_config_and_existing_skill(self):
        with tempfile.TemporaryDirectory() as temporary:
            workbuddy_home = Path(temporary) / ".workbuddy"
            config = workbuddy_home / "mcp.json"
            config.parent.mkdir(parents=True)
            original = {"mcpServers": {"existing": {"command": "keep-me"}}}
            config.write_text(json.dumps(original), encoding="utf-8")
            (workbuddy_home / "host-settings.json").write_text(
                json.dumps({"theme": "kept"}), encoding="utf-8"
            )
            old_chatweb = workbuddy_home / "skills" / "chatweb"
            old_chatweb.mkdir(parents=True)
            (old_chatweb / "old-marker.txt").write_text("restore me", encoding="utf-8")
            unrelated = workbuddy_home / "skills" / "teacher-helper"
            unrelated.mkdir(parents=True)
            (unrelated / "SKILL.md").write_text("---\nname: teacher-helper\n---\n", encoding="utf-8")

            try:
                installed = self.installer.install(
                    config,
                    python_executable="python",
                    source_skills=ROOT / "skills",
                    transaction_root=Path(temporary) / "global-chatmaker-state",
                )
            except TypeError as exc:
                self.fail(f"WorkBuddy installer does not support Skill installation: {exc}")

            self.assertTrue(installed["success"])
            self.assertEqual(installed["installed_skills"], ["chatmaker", "chatduino", "chatweb", "chatcad"])
            self.assertEqual(installed["content_manager"], "chatmaker-pack")
            self.assertEqual(installed["knowledge_packs_installed"], [])
            self.assertTrue((workbuddy_home / "skills" / "chatmaker" / "SKILL.md").is_file())
            operation_manifest = json.loads(
                Path(installed["manifest"]).read_text(encoding="utf-8")
            )
            installed_skill_names = {
                entry["name"]
                for entry in json.loads(
                    Path(operation_manifest["skill_manifest"]).read_text(encoding="utf-8")
                )["entries"]
            }
            self.assertEqual(installed_skill_names, {"chatmaker", "chatduino", "chatweb", "chatcad"})
            self.assertEqual(
                {path.name for path in (workbuddy_home / "skills").iterdir()},
                {"chatmaker", "chatduino", "chatweb", "chatcad", "teacher-helper"},
            )
            self.assertTrue(Path(installed["manifest"]).is_file())
            self.assertEqual(
                json.loads((workbuddy_home / "host-settings.json").read_text(encoding="utf-8")),
                {"theme": "kept"},
            )
            health = self.installer.doctor(config)
            self.assertEqual(health["content_manager"], "chatmaker-pack")
            self.assertEqual(health["knowledge_packs_installed"], [])

            removed = self.installer.uninstall(
                config,
                transaction_root=Path(temporary) / "global-chatmaker-state",
            )
            restored_config = json.loads(config.read_text(encoding="utf-8"))

            self.assertTrue(removed["success"])
            self.assertEqual(restored_config, original)
            self.assertEqual(
                json.loads((workbuddy_home / "host-settings.json").read_text(encoding="utf-8")),
                {"theme": "kept"},
            )
            self.assertEqual(
                (old_chatweb / "old-marker.txt").read_text(encoding="utf-8"),
                "restore me",
            )
            self.assertFalse((workbuddy_home / "skills" / "chatmaker").exists())
            self.assertTrue((workbuddy_home / "skills" / "teacher-helper" / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
