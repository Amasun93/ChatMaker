from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ADAPTER_PATH = ROOT / "runtime" / "chatmaker" / "hardware" / "esp32_devkit_v1.py"


def load_adapter():
    if not ADAPTER_PATH.is_file():
        return None
    spec = importlib.util.spec_from_file_location("chatmaker_esp32_devkit_v1", ADAPTER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class Esp32DevKitV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adapter = load_adapter()

    def test_adapter_uses_exact_official_doit_profile(self):
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")
        self.assertEqual(
            self.adapter.TARGET_FQBN,
            "esp32:esp32:esp32doit-devkit-v1",
        )
        self.assertEqual(self.adapter.REQUIRED_CORE_VERSION, "3.3.11")

    def test_core_inventory_rejects_mindplus_variants_and_requires_locked_core(self):
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")
        wrong = self.adapter.select_exact_core(
            [
                {"id": "mindplus:esp32", "installed": "0.0.1"},
                {"id": "esp32:esp32", "installed": "3.3.10"},
            ]
        )
        exact = self.adapter.select_exact_core(
            [{"id": "esp32:esp32", "installed": "3.3.11"}]
        )

        self.assertIsNone(wrong)
        self.assertEqual(exact["id"], "esp32:esp32")
        self.assertEqual(exact["installed"], "3.3.11")

    def test_module_label_alone_does_not_confirm_carrier_board(self):
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")
        unresolved = self.adapter.confirm_board_identity("ESP-WROOM-32")
        confirmed = self.adapter.confirm_board_identity(
            "doit-esp32-devkit-v1-wroom32"
        )
        mismatch = self.adapter.confirm_board_identity("fireBeetleEsp32")

        self.assertEqual(unresolved["status"], "unresolved")
        self.assertEqual(confirmed["status"], "confirmed")
        self.assertEqual(mismatch["status"], "mismatch")

    def test_port_selection_requires_confirmed_board_and_one_wired_port(self):
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")
        ports = [
            {"address": "COM3", "is_bluetooth": True, "eligible_for_upload": False},
            {"address": "COM8", "is_bluetooth": False, "eligible_for_upload": True},
        ]

        unresolved = self.adapter.select_upload_port(ports, board_profile=None)
        selected = self.adapter.select_upload_port(
            ports,
            board_profile="doit-esp32-devkit-v1-wroom32",
        )
        bluetooth = self.adapter.select_upload_port(
            ports,
            board_profile="doit-esp32-devkit-v1-wroom32",
            requested="COM3",
        )

        self.assertEqual(unresolved, (None, "board_identity_confirmation_required"))
        self.assertEqual(selected, ("COM8", None))
        self.assertEqual(bluetooth, (None, "bluetooth_port_rejected"))

    def test_compile_command_and_artifact_are_esp32_specific(self):
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sketch_dir = root / "blink"
            sketch_dir.mkdir()
            (sketch_dir / "blink.ino").write_text(
                "void setup() {}\nvoid loop() {}\n",
                encoding="utf-8",
            )
            build_dir = root / "build"
            command = self.adapter.build_compile_command(
                {"cli": "arduino-cli", "config": "arduino-cli.yaml"},
                sketch_dir,
                build_dir,
            )
            build_dir.mkdir()
            (build_dir / "blink.ino.bin").write_bytes(b"firmware")

            artifact = self.adapter.find_application_binary(build_dir)

        self.assertIn("esp32:esp32:esp32doit-devkit-v1", command)
        self.assertNotIn("fireBeetleEsp32", " ".join(command))
        self.assertNotIn("mindplus:esp32", " ".join(command))
        self.assertEqual(artifact.name, "blink.ino.bin")

    def test_doctor_reports_missing_exact_toolchain_without_installing(self):
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")
        result = self.adapter.doctor_result(
            candidates=[
                {
                    "backend": "mindplus-2-cli",
                    "cli": "mindplus-arduino-cli",
                    "core_inventory": [
                        {"id": "mindplus:esp32", "installed": "0.0.1"}
                    ],
                }
            ],
            ports=[],
        )

        self.assertFalse(result["success"])
        self.assertFalse(result["ready_for_compile"])
        self.assertEqual(result["error"], "exact_esp32_toolchain_missing")
        self.assertFalse(result["installation_performed"])
        self.assertEqual(result["required_fqbn"], self.adapter.TARGET_FQBN)

    def test_probe_requires_exact_core_and_matching_board_details(self):
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")
        calls: list[list[str]] = []

        def runner(command, timeout):
            calls.append(command)
            if command[1:3] == ["core", "list"]:
                return {
                    "returncode": 0,
                    "stdout": json.dumps(
                        [
                            {
                                "id": "esp32:esp32",
                                "installed": "3.3.11",
                                "name": "esp32",
                                "boards": [{"name": "many", "fqbn": "esp32:esp32:esp32"}],
                            }
                        ]
                    ),
                    "stderr": "",
                }
            return {
                "returncode": 0,
                "stdout": json.dumps(
                    {
                        "fqbn": "esp32:esp32:esp32doit-devkit-v1",
                        "name": "DOIT ESP32 DEVKIT V1",
                    }
                ),
                "stderr": "",
            }

        result = self.adapter.probe_candidate(
            {"backend": "arduino-cli", "cli": "arduino-cli"},
            runner=runner,
        )

        self.assertTrue(result["ready_for_compile"])
        self.assertTrue(result["fqbn_details_verified"])
        self.assertEqual(result["core_version"], "3.3.11")
        self.assertEqual(len(calls), 2)
        self.assertIn(self.adapter.TARGET_FQBN, calls[1])
        self.assertNotIn("stdout", result["core_execution"])
        self.assertNotIn("stdout", result["board_details_execution"])
        self.assertNotIn("boards", result["core_inventory"][0])

    def test_probe_stops_before_board_details_for_mindplus_only_core(self):
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")
        calls: list[list[str]] = []

        def runner(command, timeout):
            calls.append(command)
            return {
                "returncode": 0,
                "stdout": json.dumps(
                    [{"id": "mindplus:esp32", "installed": "0.0.1"}]
                ),
                "stderr": "",
            }

        result = self.adapter.probe_candidate(
            {"backend": "mindplus-2-cli", "cli": "mindplus-arduino-cli"},
            runner=runner,
        )

        self.assertFalse(result["ready_for_compile"])
        self.assertEqual(result["error"], "exact_esp32_core_not_found")
        self.assertEqual(len(calls), 1)

    def test_doctor_request_probes_candidates_but_never_installs(self):
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")
        original_discover = self.adapter.discover_cli_candidates
        original_probe = self.adapter.probe_candidate
        original_ports = self.adapter.scan_ports
        self.adapter.discover_cli_candidates = lambda: [
            {"backend": "arduino-ide-cli", "cli": "arduino-cli"}
        ]
        self.adapter.probe_candidate = lambda candidate, runner: {
            **candidate,
            "core_inventory": [{"id": "arduino:avr", "installed": "1.8.6"}],
            "ready_for_compile": False,
            "fqbn_details_verified": False,
            "error": "exact_esp32_core_not_found",
        }
        self.adapter.scan_ports = lambda: []
        try:
            result = self.adapter.execute_request({"action": "doctor"})
        finally:
            self.adapter.discover_cli_candidates = original_discover
            self.adapter.probe_candidate = original_probe
            self.adapter.scan_ports = original_ports

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "exact_esp32_toolchain_missing")
        self.assertFalse(result["installation_performed"])
        self.assertNotIn("download", result)
        self.assertNotIn("installer", result)

    def test_compile_requires_confirmed_profile_and_creates_esp32_binary(self):
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")
        calls: list[list[str]] = []

        def runner(command, timeout):
            calls.append(command)
            build_dir = Path(command[command.index("--build-path") + 1])
            build_dir.mkdir(parents=True, exist_ok=True)
            (build_dir / "blink.ino.bin").write_bytes(b"firmware")
            return {"returncode": 0, "stdout": "Sketch uses 200000 bytes", "stderr": ""}

        with tempfile.TemporaryDirectory() as directory:
            sketch_dir = Path(directory) / "blink"
            sketch_dir.mkdir()
            sketch = sketch_dir / "blink.ino"
            sketch.write_text("void setup(){}\nvoid loop(){}\n", encoding="utf-8")
            context = {
                "cli": "arduino-cli",
                "core_version": "3.3.11",
                "ready_for_compile": True,
                "fqbn_details_verified": True,
            }
            unresolved = self.adapter.compile_result(
                context,
                {"sketch": str(sketch), "board_profile": "ESP-WROOM-32"},
                runner=runner,
            )
            compiled = self.adapter.compile_result(
                context,
                {
                    "sketch": str(sketch),
                    "board_profile": "doit-esp32-devkit-v1-wroom32",
                },
                runner=runner,
            )

        self.assertFalse(unresolved["success"])
        self.assertEqual(unresolved["error"], "board_identity_confirmation_required")
        self.assertTrue(compiled["success"])
        self.assertEqual(compiled["fqbn"], self.adapter.TARGET_FQBN)
        self.assertTrue(compiled["application_bin"].endswith("blink.ino.bin"))
        self.assertEqual(len(calls), 1)

    def test_compile_request_uses_probed_exact_toolchain(self):
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")

        def runner(command, timeout):
            if command[1:3] == ["core", "list"]:
                return {
                    "returncode": 0,
                    "stdout": json.dumps(
                        [{"id": "esp32:esp32", "installed": "3.3.11"}]
                    ),
                    "stderr": "",
                }
            if command[1:3] == ["board", "details"]:
                return {
                    "returncode": 0,
                    "stdout": json.dumps(
                        {
                            "fqbn": "esp32:esp32:esp32doit-devkit-v1",
                            "name": "DOIT ESP32 DEVKIT V1",
                        }
                    ),
                    "stderr": "",
                }
            build_dir = Path(command[command.index("--build-path") + 1])
            build_dir.mkdir(parents=True, exist_ok=True)
            (build_dir / "blink.ino.bin").write_bytes(b"firmware")
            return {"returncode": 0, "stdout": "compiled", "stderr": ""}

        with tempfile.TemporaryDirectory() as directory:
            sketch_dir = Path(directory) / "blink"
            sketch_dir.mkdir()
            sketch = sketch_dir / "blink.ino"
            sketch.write_text("void setup(){}\nvoid loop(){}\n", encoding="utf-8")
            result = self.adapter.execute_request(
                {
                    "action": "compile",
                    "sketch": str(sketch),
                    "board_profile": "doit-esp32-devkit-v1-wroom32",
                },
                candidates=[{"backend": "arduino-cli", "cli": "arduino-cli"}],
                ports=[],
                runner=runner,
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["fqbn"], self.adapter.TARGET_FQBN)

    def test_compile_request_accepts_complete_code_for_ai_hosts(self):
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")

        def runner(command, timeout):
            if command[1:3] == ["core", "list"]:
                return {
                    "returncode": 0,
                    "stdout": json.dumps(
                        [{"id": "esp32:esp32", "installed": "3.3.11"}]
                    ),
                    "stderr": "",
                }
            if command[1:3] == ["board", "details"]:
                return {
                    "returncode": 0,
                    "stdout": json.dumps(
                        {
                            "fqbn": "esp32:esp32:esp32doit-devkit-v1",
                            "name": "DOIT ESP32 DEVKIT V1",
                        }
                    ),
                    "stderr": "",
                }
            sketch_dir = Path(command[-1])
            self.assertTrue((sketch_dir / f"{sketch_dir.name}.ino").is_file())
            build_dir = Path(command[command.index("--build-path") + 1])
            build_dir.mkdir(parents=True, exist_ok=True)
            (build_dir / f"{sketch_dir.name}.ino.bin").write_bytes(b"firmware")
            return {"returncode": 0, "stdout": "compiled", "stderr": ""}

        result = self.adapter.execute_request(
            {
                "action": "compile",
                "code": "void setup(){}\nvoid loop(){}\n",
                "project_name": "esp32-host-smoke",
                "board_profile": "doit-esp32-devkit-v1-wroom32",
            },
            candidates=[{"backend": "arduino-cli", "cli": "arduino-cli"}],
            ports=[],
            runner=runner,
        )

        self.assertTrue(result["success"])
        self.assertIn("esp32-host-smoke", result["sketch"])


if __name__ == "__main__":
    unittest.main()
