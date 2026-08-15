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
            cache_dir = root / "cache"
            command = self.adapter.build_compile_command(
                {"cli": "arduino-cli", "config": "arduino-cli.yaml"},
                sketch_dir,
                build_dir,
                cache_dir,
            )
            build_dir.mkdir()
            (build_dir / "blink.ino.bin").write_bytes(b"firmware")

            artifact = self.adapter.find_application_binary(build_dir)

        self.assertIn("esp32:esp32:esp32doit-devkit-v1", command)
        self.assertIn("--build-cache-path", command)
        self.assertIn(str(cache_dir), command)
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

    def test_prepare_environment_exact_ready_is_a_single_noop_probe(self):
        """Catches a ready environment unnecessarily checking the index or probing twice."""
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")
        calls: list[list[str]] = []

        def runner(command, timeout):
            calls.append(command)
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
            self.fail(f"a ready environment must not execute: {command}")

        result = self.adapter.execute_request(
            {"action": "prepare-environment"},
            candidates=[{"backend": "arduino-ide-cli", "cli": "arduino-cli"}],
            ports=[],
            runner=runner,
        )

        self.assertTrue(result["success"])
        self.assertTrue(result["ready_for_compile"])
        self.assertFalse(result["update_checked"])
        self.assertFalse(result["update_performed"])
        self.assertFalse(result["installation_performed"])
        self.assertEqual(result["required_core"], "esp32:esp32@3.3.11")
        self.assertEqual(result["required_fqbn"], self.adapter.TARGET_FQBN)
        self.assertEqual(len(calls), 2)

    def test_prepare_environment_exact_ready_wins_over_another_unreadable_candidate(self):
        """An already verified official environment needs no mutation despite another broken CLI."""
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")
        calls: list[list[str]] = []

        def runner(command, timeout):
            calls.append(command)
            cli = command[0]
            if cli == "arduino-cli-ready" and command[1:3] == ["core", "list"]:
                return {
                    "returncode": 0,
                    "stdout": json.dumps(
                        [{"id": "esp32:esp32", "installed": "3.3.11"}]
                    ),
                    "stderr": "",
                }
            if cli == "arduino-cli-ready" and command[1:3] == ["board", "details"]:
                return {
                    "returncode": 0,
                    "stdout": json.dumps(
                        {
                            "fqbn": self.adapter.TARGET_FQBN,
                            "name": "DOIT ESP32 DEVKIT V1",
                        }
                    ),
                    "stderr": "",
                }
            if cli == "arduino-cli-bad" and command[1:3] == ["core", "list"]:
                return {"returncode": 1, "stdout": "[]", "stderr": "broken"}
            self.fail(f"a ready environment must not execute: {command}")

        result = self.adapter.execute_request(
            {"action": "prepare-environment"},
            candidates=[
                {"backend": "arduino-ide-cli", "cli": "arduino-cli-ready"},
                {"backend": "path-arduino-cli", "cli": "arduino-cli-bad"},
            ],
            ports=[],
            runner=runner,
        )

        self.assertTrue(result["success"])
        self.assertTrue(result["ready_for_compile"])
        self.assertFalse(result["update_checked"])
        self.assertFalse(result["update_performed"])
        self.assertFalse(result["installation_performed"])
        self.assertEqual(len(calls), 3)

    def test_prepare_environment_installs_only_the_locked_target_when_missing(self):
        """Catches an install that uses latest, a substitute core, or skips final FQBN verification."""
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")
        installed = False
        calls: list[list[str]] = []

        def runner(command, timeout):
            nonlocal installed
            calls.append(command)
            if command[1:3] == ["core", "list"]:
                inventory = [{"id": "esp32:esp32", "installed": "3.3.11"}] if installed else []
                return {"returncode": 0, "stdout": json.dumps(inventory), "stderr": ""}
            if command[1:3] == ["core", "update-index"]:
                return {"returncode": 0, "stdout": "index updated", "stderr": ""}
            if command[1:3] == ["core", "install"]:
                self.assertIn("esp32:esp32@3.3.11", command)
                installed = True
                return {"returncode": 0, "stdout": "installed", "stderr": ""}
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
            self.fail(f"unexpected Arduino CLI command: {command}")

        result = self.adapter.execute_request(
            {"action": "prepare-environment"},
            candidates=[{"backend": "arduino-ide-cli", "cli": "arduino-cli"}],
            ports=[],
            runner=runner,
        )

        command_text = "\n".join(" ".join(command) for command in calls)
        self.assertTrue(result["success"])
        self.assertTrue(result["update_checked"])
        self.assertTrue(result["update_performed"])
        self.assertTrue(result["installation_performed"])
        self.assertTrue(result["ready_for_compile"])
        self.assertTrue(result["fqbn_details_verified"])
        self.assertIn(self.adapter.ESP32_PACKAGE_INDEX_URL, command_text)
        self.assertNotIn("latest", command_text)
        self.assertNotIn("mindplus:esp32", command_text)
        self.assertNotIn("firebeetle", command_text.casefold())

    def test_prepare_environment_refuses_to_downgrade_a_newer_official_core(self):
        """Catches a future toolchain replacing a newer official core with the verified lock."""
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")
        calls: list[list[str]] = []

        def runner(command, timeout):
            calls.append(command)
            self.assertEqual(command[1:3], ["core", "list"])
            return {
                "returncode": 0,
                "stdout": json.dumps([{"id": "esp32:esp32", "installed": "3.4.0"}]),
                "stderr": "",
            }

        result = self.adapter.execute_request(
            {"action": "prepare-environment"},
            candidates=[{"backend": "arduino-ide-cli", "cli": "arduino-cli"}],
            ports=[],
            runner=runner,
        )

        self.assertFalse(result["success"])
        self.assertFalse(result["ready_for_compile"])
        self.assertEqual(result["error"], "installed_core_newer_than_verified_target")
        self.assertFalse(result["update_checked"])
        self.assertFalse(result["installation_performed"])
        self.assertEqual(len(calls), 1)

    def test_prepare_environment_does_not_treat_a_mindplus_cli_as_the_official_target(self):
        """Catches preparation declaring a Mind+ ESP32 environment ready for the standalone target."""
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
            self.fail(f"a Mind+ candidate must not update or install: {command}")

        result = self.adapter.execute_request(
            {"action": "prepare-environment"},
            candidates=[{"backend": "mindplus-2-cli", "cli": "mindplus-arduino-cli"}],
            ports=[],
            runner=runner,
        )

        self.assertFalse(result["success"])
        self.assertFalse(result["ready_for_compile"])
        self.assertEqual(result["error"], "official_arduino_cli_not_found")
        self.assertFalse(result["installation_performed"])

    def test_prepare_environment_does_not_replace_an_unknown_official_version(self):
        """Catches an unrecognised installed official version being replaced automatically."""
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")
        calls: list[list[str]] = []

        def runner(command, timeout):
            calls.append(command)
            return {
                "returncode": 0,
                "stdout": json.dumps(
                    [{"id": "esp32:esp32", "installed": "3.3.11-rc1"}]
                ),
                "stderr": "",
            }

        result = self.adapter.execute_request(
            {"action": "prepare-environment"},
            candidates=[{"backend": "arduino-ide-cli", "cli": "arduino-cli"}],
            ports=[],
            runner=runner,
        )

        self.assertFalse(result["success"])
        self.assertFalse(result["ready_for_compile"])
        self.assertEqual(result["error"], "installed_core_version_not_auto_replaceable")
        self.assertFalse(result["update_checked"])
        self.assertFalse(result["installation_performed"])
        self.assertEqual(len(calls), 1)

    def test_prepare_environment_reports_failed_install_without_claiming_ready(self):
        """Catches a failed install being reported as a compile-ready environment."""
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")

        def runner(command, timeout):
            if command[1:3] == ["core", "list"]:
                return {"returncode": 0, "stdout": "[]", "stderr": ""}
            if command[1:3] == ["core", "update-index"]:
                return {"returncode": 0, "stdout": "index updated", "stderr": ""}
            if command[1:3] == ["core", "install"]:
                return {"returncode": 1, "stdout": "", "stderr": "download failed"}
            self.fail(f"unexpected Arduino CLI command: {command}")

        result = self.adapter.execute_request(
            {"action": "prepare-environment"},
            candidates=[{"backend": "arduino-ide-cli", "cli": "arduino-cli"}],
            ports=[],
            runner=runner,
        )

        self.assertFalse(result["success"])
        self.assertFalse(result["ready_for_compile"])
        self.assertEqual(result["error"], "esp32_core_install_failed")
        self.assertTrue(result["update_checked"])
        self.assertTrue(result["update_performed"])
        self.assertFalse(result["installation_performed"])
        self.assertIn("install_execution", result)

    def test_prepare_environment_fails_closed_when_core_inventory_cannot_be_read(self):
        """A broken inventory is not evidence that the locked core is absent."""
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")
        for label, execution in (
            ("nonzero", {"returncode": 1, "stdout": "[]", "stderr": "broken"}),
            ("nonjson", {"returncode": 0, "stdout": "not json", "stderr": ""}),
            ("nonlist", {"returncode": 0, "stdout": "{}", "stderr": ""}),
            ("timeout", {"returncode": None, "stdout": "", "stderr": "TimeoutExpired"}),
        ):
            with self.subTest(label=label):
                calls: list[list[str]] = []

                def runner(command, timeout):
                    calls.append(command)
                    return execution

                result = self.adapter.execute_request(
                    {"action": "prepare-environment"},
                    candidates=[{"backend": "arduino-ide-cli", "cli": "arduino-cli"}],
                    ports=[],
                    runner=runner,
                )

                self.assertFalse(result["success"])
                self.assertFalse(result["update_checked"])
                self.assertFalse(result["installation_performed"])
                self.assertEqual(result["error"], "esp32_core_inventory_unavailable")
                self.assertEqual(len(calls), 1)

    def test_prepare_environment_mixed_candidates_fail_closed_before_install(self):
        """A broken official candidate blocks install, even if another official CLI reports an empty list."""
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")
        calls: list[list[str]] = []

        def runner(command, timeout):
            calls.append(command)
            cli = command[0]
            if cli == "arduino-cli-bad":
                return {"returncode": 1, "stdout": "[]", "stderr": "broken"}
            if cli == "arduino-cli-good":
                return {"returncode": 0, "stdout": "[]", "stderr": ""}
            self.fail(f"unexpected Arduino CLI command: {command}")

        result = self.adapter.execute_request(
            {"action": "prepare-environment"},
            candidates=[
                {"backend": "arduino-ide-cli", "cli": "arduino-cli-bad"},
                {"backend": "arduino-ide-cli", "cli": "arduino-cli-good"},
            ],
            ports=[],
            runner=runner,
        )

        self.assertFalse(result["success"])
        self.assertFalse(result["update_checked"])
        self.assertFalse(result["update_performed"])
        self.assertFalse(result["installation_performed"])
        self.assertEqual(result["error"], "esp32_core_inventory_unavailable")
        self.assertEqual(
            calls,
            [
                ["arduino-cli-bad", "core", "list", "--format", "jsonmini"],
                ["arduino-cli-good", "core", "list", "--format", "jsonmini"],
            ],
        )

    def test_prepare_environment_does_not_treat_equivalent_numeric_version_as_exact(self):
        """3.3.11.0 must never silently turn into the separately verified 3.3.11."""
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")
        calls: list[list[str]] = []

        def runner(command, timeout):
            calls.append(command)
            return {
                "returncode": 0,
                "stdout": json.dumps([{"id": "esp32:esp32", "installed": "3.3.11.0"}]),
                "stderr": "",
            }

        result = self.adapter.execute_request(
            {"action": "prepare-environment"},
            candidates=[{"backend": "arduino-ide-cli", "cli": "arduino-cli"}],
            ports=[],
            runner=runner,
        )

        self.assertFalse(result["success"])
        self.assertFalse(result["update_checked"])
        self.assertFalse(result["installation_performed"])
        self.assertEqual(result["error"], "installed_core_version_not_auto_replaceable")
        self.assertEqual(len(calls), 1)

    def test_prepare_environment_failed_install_stays_not_ready_even_if_reprobe_looks_ready(self):
        """A nonzero installer result remains a failed preparation, even after a partial install."""
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")
        installed = False

        def runner(command, timeout):
            nonlocal installed
            if command[1:3] == ["core", "list"]:
                inventory = [{"id": "esp32:esp32", "installed": "3.3.11"}] if installed else []
                return {"returncode": 0, "stdout": json.dumps(inventory), "stderr": ""}
            if command[1:3] == ["core", "update-index"]:
                return {"returncode": 0, "stdout": "index updated", "stderr": ""}
            if command[1:3] == ["core", "install"]:
                installed = True
                return {"returncode": 1, "stdout": "partial", "stderr": "interrupted"}
            if command[1:3] == ["board", "details"]:
                return {
                    "returncode": 0,
                    "stdout": json.dumps(
                        {"fqbn": self.adapter.TARGET_FQBN, "name": "DOIT ESP32 DEVKIT V1"}
                    ),
                    "stderr": "",
                }
            self.fail(f"unexpected Arduino CLI command: {command}")

        result = self.adapter.execute_request(
            {"action": "prepare-environment"},
            candidates=[{"backend": "arduino-ide-cli", "cli": "arduino-cli"}],
            ports=[],
            runner=runner,
        )

        self.assertFalse(result["success"])
        self.assertFalse(result["ready_for_compile"])
        self.assertFalse(result["fqbn_details_verified"])
        self.assertEqual(result["error"], "esp32_core_install_failed")
        self.assertTrue(result["probe_after"][0]["ready_for_compile"])

    def test_mindplus_candidate_with_exact_strings_is_rejected_for_doctor_and_compile(self):
        """ESP32 may not borrow a Mind+ CLI, even when its output claims the official target."""
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")
        calls: list[list[str]] = []

        def runner(command, timeout):
            calls.append(command)
            return {"returncode": 0, "stdout": "[]", "stderr": ""}

        candidate = {"backend": "mindplus-2-cli", "cli": "mindplus-arduino-cli"}
        doctor = self.adapter.execute_request(
            {"action": "doctor"}, candidates=[candidate], ports=[], runner=runner
        )
        compile_result = self.adapter.execute_request(
            {
                "action": "compile",
                "code": "void setup(){} void loop(){}",
                "board_profile": "doit-esp32-devkit-v1-wroom32",
            },
            candidates=[candidate],
            ports=[],
            runner=runner,
        )

        self.assertFalse(doctor["success"])
        self.assertFalse(compile_result["success"])
        self.assertEqual(doctor["error"], "exact_esp32_toolchain_missing")
        self.assertEqual(compile_result["error"], "exact_esp32_toolchain_missing")
        self.assertEqual(calls, [])

    def test_prepare_environment_uses_compact_environment_summary(self):
        """Preparation output must not echo large board-details payloads to the host."""
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")
        large_details = {"fqbn": self.adapter.TARGET_FQBN, "name": "DOIT ESP32 DEVKIT V1", "options": "x" * 50000}

        def runner(command, timeout):
            if command[1:3] == ["core", "list"]:
                return {
                    "returncode": 0,
                    "stdout": json.dumps([{"id": "esp32:esp32", "installed": "3.3.11"}]),
                    "stderr": "",
                }
            return {"returncode": 0, "stdout": json.dumps(large_details), "stderr": ""}

        result = self.adapter.execute_request(
            {"action": "prepare-environment"},
            candidates=[{"backend": "arduino-ide-cli", "cli": "arduino-cli"}],
            ports=[],
            runner=runner,
        )

        self.assertTrue(result["success"])
        self.assertNotIn("board_details", result["environment"])
        self.assertLess(len(json.dumps(result)), 10000)

    def test_compile_requires_confirmed_profile_and_creates_esp32_binary(self):
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")
        calls: list[list[str]] = []

        def runner(command, timeout):
            calls.append(command)
            build_dir = Path(command[command.index("--build-path") + 1])
            cache_dir = Path(command[command.index("--build-cache-path") + 1])
            build_dir.mkdir(parents=True, exist_ok=True)
            cache_dir.mkdir(parents=True, exist_ok=True)
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
        self.assertIn("build_cache_dir", compiled)
        self.assertEqual(len(calls), 1)

    def test_compile_build_dir_tracks_sketch_location_and_cleans_nested_stale_state(self):
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")
        calls: list[list[str]] = []

        def runner(command, timeout):
            calls.append(command)
            build_dir = Path(command[command.index("--build-path") + 1])
            cache_dir = Path(command[command.index("--build-cache-path") + 1])
            self.assertEqual(build_dir.parent.name, ".chatmaker-esp32-builds")
            self.assertEqual(build_dir.parent.parent, sketch_dir.parent)
            self.assertEqual(cache_dir.parent.name, ".chatmaker-esp32-cache")
            self.assertEqual(cache_dir.parent.parent, sketch_dir.parent)
            self.assertEqual(cache_dir.drive, build_dir.drive)
            build_dir.mkdir(parents=True, exist_ok=True)
            (build_dir / "blink.ino.bin").write_bytes(b"fresh-firmware")
            return {"returncode": 0, "stdout": "compiled", "stderr": ""}

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
            digest = self.adapter._build_digest(sketch, context["core_version"])
            stale_build_dir = self.adapter.build_dir_for_sketch(sketch_dir, digest)
            stable_cache_dir = self.adapter.build_cache_dir_for_sketch(
                sketch_dir,
                context["core_version"],
            )
            stale_nested = stale_build_dir / "stale" / "nested"
            stale_nested.mkdir(parents=True)
            (stale_nested / "old.txt").write_text("old", encoding="utf-8")
            stable_cache_dir.mkdir(parents=True)
            (stable_cache_dir / "cache.marker").write_text("keep", encoding="utf-8")

            first = self.adapter.compile_result(
                context,
                {
                    "sketch": str(sketch),
                    "board_profile": "doit-esp32-devkit-v1-wroom32",
                },
                runner=runner,
            )
            second = self.adapter.compile_result(
                context,
                {
                    "sketch": str(sketch),
                    "board_profile": "doit-esp32-devkit-v1-wroom32",
                },
                runner=runner,
            )

            build_dir = Path(first["build_dir"])
            self.assertEqual(build_dir, stale_build_dir)
            self.assertEqual(Path(second["build_dir"]), build_dir)
            self.assertEqual(Path(first["build_cache_dir"]), stable_cache_dir)
            self.assertEqual(Path(second["build_cache_dir"]), stable_cache_dir)
            self.assertFalse((build_dir / "stale").exists())
            self.assertEqual((build_dir / "blink.ino.bin").read_bytes(), b"fresh-firmware")
            self.assertEqual(
                (stable_cache_dir / "cache.marker").read_text(encoding="utf-8"),
                "keep",
            )

        self.assertEqual(len(calls), 2)

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
            cache_dir = Path(command[command.index("--build-cache-path") + 1])
            build_dir.mkdir(parents=True, exist_ok=True)
            cache_dir.mkdir(parents=True, exist_ok=True)
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
            cache_dir = Path(command[command.index("--build-cache-path") + 1])
            build_dir.mkdir(parents=True, exist_ok=True)
            cache_dir.mkdir(parents=True, exist_ok=True)
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

    def test_upload_uses_exact_fqbn_without_board_fallback(self):
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")
        with tempfile.TemporaryDirectory() as directory:
            build_dir = Path(directory)
            application_bin = build_dir / "blink.ino.bin"
            application_bin.write_bytes(b"firmware")
            calls: list[list[str]] = []

            def runner(command, timeout):
                calls.append(command)
                return {"returncode": 0, "stdout": "Upload complete", "stderr": ""}

            result = self.adapter.upload_result(
                {"cli": "arduino-cli", "config": "arduino-cli.yaml"},
                {
                    "board_profile": "doit-esp32-devkit-v1-wroom32",
                    "port": "COM8",
                },
                {
                    "success": True,
                    "build_dir": str(build_dir),
                    "application_bin": str(application_bin),
                },
                ports=[
                    {
                        "address": "COM8",
                        "is_bluetooth": False,
                        "eligible_for_upload": True,
                    }
                ],
                runner=runner,
            )

        self.assertTrue(result["success"])
        self.assertTrue(result["firmware_uploaded"])
        self.assertFalse(result["hardware_runtime_verified"])
        self.assertEqual(len(calls), 1)
        command_text = " ".join(calls[0])
        self.assertIn("esp32:esp32:esp32doit-devkit-v1", command_text)
        self.assertNotIn("fireBeetle", command_text)
        self.assertNotIn("mindplus:esp32", command_text)

    def test_compile_upload_waits_for_hardware_after_compile(self):
        self.assertIsNotNone(self.adapter, "ESP32 DevKit V1 adapter is missing")
        result = self.adapter.compile_upload_result(
            {"ready_for_compile": True},
            {
                "code": "void setup(){} void loop(){}",
                "board_profile": "doit-esp32-devkit-v1-wroom32",
            },
            ports=[],
            compile_fn=lambda context, request: {
                "success": True,
                "application_bin": "blink.ino.bin",
                "build_dir": "build",
            },
            upload_fn=lambda context, request, compiled, ports: {
                "success": False,
                "error": "no_wired_upload_port_found",
                "upload_executed": False,
            },
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["stage"], "awaiting-hardware")
        self.assertTrue(result["hardware_connection_required"])
        self.assertIsNotNone(result["compile"])


if __name__ == "__main__":
    unittest.main()
