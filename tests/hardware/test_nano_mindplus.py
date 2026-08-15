import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "runtime"
sys.path.insert(0, str(RUNTIME))


def load_bridge():
    from chatmaker.hardware import nano_mindplus

    return nano_mindplus


class NanoBridgeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bridge = load_bridge()

    def test_existing_v2_is_used_without_install_recommendation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "Mind+2"
            cli = root / "applications" / "deps" / "mind-link" / "tool" / "arduino-cli.exe"
            cli.parent.mkdir(parents=True)
            cli.write_bytes(b"test")
            config = Path(temporary) / "mind+" / "Arduino" / "arduino-cli.yaml"
            config.parent.mkdir(parents=True)
            config.write_text("directories:\n  data: test\n", encoding="utf-8")

            installations = self.bridge.discover_installations(
                v1_roots=[], v2_roots=[root], v2_config_candidates=[config]
            )
            decision = self.bridge.choose_environment(installations)

            self.assertEqual(decision["selected_backend"], "mindplus-2-cli")
            self.assertFalse(decision["install_needed"])
            self.assertIsNone(decision["install_recommendation"])

    def test_default_discovery_does_not_probe_every_possible_drive(self):
        v1_roots = {str(path) for path in self.bridge.default_v1_roots()}
        v2_roots = {str(path) for path in self.bridge.default_v2_roots()}

        self.assertLessEqual(len(v1_roots), 10)
        self.assertLessEqual(len(v2_roots), 10)
        self.assertFalse(any(path.startswith("Z:") for path in v1_roots | v2_roots))

    def test_registry_install_location_is_accepted_without_drive_scan(self):
        with tempfile.TemporaryDirectory() as temporary:
            v1 = Path(temporary) / "CustomMind1"
            v2 = Path(temporary) / "CustomMind2"
            self.assertIn(v1, self.bridge.merge_discovery_roots([], [v1]))
            self.assertIn(v2, self.bridge.merge_discovery_roots([], [v2]))

    def test_existing_v1_is_used_without_install_recommendation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "Mind+"
            builder = root / "Arduino" / "arduino-builder" / "arduino-builder.exe"
            avrdude = root / "Arduino" / "hardware" / "tools" / "avr" / "bin" / "avrdude.exe"
            boards = root / "Arduino" / "hardware" / "arduino" / "avr" / "boards.txt"
            for path in (builder, avrdude, boards):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"test")

            installations = self.bridge.discover_installations(
                v1_roots=[root], v2_roots=[], v2_config_candidates=[]
            )
            decision = self.bridge.choose_environment(installations)

            self.assertEqual(decision["selected_backend"], "mindplus-1-builder")
            self.assertFalse(decision["install_needed"])

    def test_no_install_prefers_official_v1_for_windows_x64(self):
        system = {
            "os_family": "windows",
            "os_version": "11",
            "architecture": "x86_64",
            "distribution": "windows",
        }
        recommendation = self.bridge.recommend_mindplus_1x(system)

        self.assertEqual(recommendation["version"], "1.8.1 RC3.0")
        self.assertEqual(recommendation["package_type"], "exe")
        self.assertTrue(recommendation["auto_download_allowed"])
        self.assertEqual(
            recommendation["url"],
            "https://download3.dfrobot.com.cn/MindPlus_Win_V1.8.1_RC3.0.exe",
        )

    def test_windows_arm_does_not_download_unconfirmed_v1_binary(self):
        system = {
            "os_family": "windows",
            "os_version": "11",
            "architecture": "arm64",
            "distribution": "windows",
        }
        recommendation = self.bridge.recommend_mindplus_1x(system)

        self.assertFalse(recommendation["auto_download_allowed"])
        self.assertEqual(recommendation["status"], "compatibility_confirmation_required")
        self.assertEqual(recommendation["url"], "https://mindplus.cc/download.html")

    def test_linux_routes_by_distribution_and_architecture(self):
        generic = self.bridge.recommend_mindplus_1x(
            {
                "os_family": "linux",
                "os_version": "24.04",
                "architecture": "arm64",
                "distribution": "ubuntu",
            }
        )
        kylin = self.bridge.recommend_mindplus_1x(
            {
                "os_family": "linux",
                "os_version": "V10",
                "architecture": "x86_64",
                "distribution": "kylin",
            }
        )

        self.assertEqual(generic["version"], "1.7.3")
        self.assertEqual(generic["architecture"], "arm64")
        self.assertEqual(kylin["version"], "1.7.4")
        self.assertEqual(kylin["distribution"], "kylin")

    def test_port_selection_prefers_one_likely_nano_and_rejects_bluetooth(self):
        ports = [
            {
                "address": "COM3",
                "is_bluetooth": True,
                "nano_likely": False,
                "eligible_for_upload": False,
            },
            {
                "address": "COM7",
                "is_bluetooth": False,
                "nano_likely": True,
                "eligible_for_upload": True,
            },
            {
                "address": "COM9",
                "is_bluetooth": False,
                "nano_likely": False,
                "eligible_for_upload": True,
            },
        ]

        selected, error = self.bridge.select_upload_port(ports)
        rejected, rejected_error = self.bridge.select_upload_port(ports, requested="COM3")

        self.assertEqual(selected, "COM7")
        self.assertIsNone(error)
        self.assertIsNone(rejected)
        self.assertEqual(rejected_error, "bluetooth_port_rejected")

    def test_multiple_unknown_wired_ports_require_selection(self):
        ports = [
            {"address": "COM5", "is_bluetooth": False, "nano_likely": False, "eligible_for_upload": True},
            {"address": "COM6", "is_bluetooth": False, "nano_likely": False, "eligible_for_upload": True},
        ]

        selected, error = self.bridge.select_upload_port(ports)

        self.assertIsNone(selected)
        self.assertEqual(error, "multiple_wired_ports_require_selection")

    def test_v1_and_v2_use_distinct_nano_fqbn(self):
        self.assertEqual(
            self.bridge.fqbn_for_backend("mindplus-1-builder"),
            "arduino:avr:nano:cpu=atmega328",
        )
        self.assertEqual(
            self.bridge.fqbn_for_backend("mindplus-2-cli"),
            "mindplus:avr:nano:cpu=atmega328",
        )

    def test_pin_validator_rejects_nano_only_constraints(self):
        errors = self.bridge.validate_pin_assignments(
            [
                {"module": "LED", "pin": "A6", "mode": "digital_output"},
                {"module": "servo", "pin": "D4", "mode": "pwm_output"},
                {"module": "sensor", "pin": "D0", "mode": "digital_input"},
            ]
        )

        codes = {item["code"] for item in errors}
        self.assertIn("a6_a7_analog_input_only", codes)
        self.assertIn("pin_has_no_pwm", codes)
        self.assertIn("usb_serial_pin_conflict", codes)

    def test_prepare_code_creates_valid_arduino_sketch(self):
        sketch = self.bridge.prepare_code(
            "void setup(){}\nvoid loop(){}\n", "光敏 LED 实验"
        )

        self.assertTrue(sketch.is_dir())
        self.assertTrue((sketch / f"{sketch.name}.ino").is_file())
        self.assertRegex(sketch.name, r"^[A-Za-z0-9_-]+-[0-9a-f]{12}$")

    def test_v2_compile_command_uses_mindplus_nano_and_config(self):
        context = {
            "backend": "mindplus-2-cli",
            "cli": r"E:\Mind+2\arduino-cli.exe",
            "config": r"C:\mind+\Arduino\arduino-cli.yaml",
        }
        sketch = Path(r"C:\tmp\blink\blink.ino")
        command = self.bridge.build_compile_command(
            context, sketch, Path(r"C:\tmp\build")
        )

        joined = " ".join(command)
        self.assertIn("mindplus:avr:nano:cpu=atmega328", joined)
        self.assertIn("--config-file", command)
        self.assertIn("compile", command)

    def test_v1_compile_command_uses_arduino_nano_fqbn(self):
        context = {
            "backend": "mindplus-1-builder",
            "builder": r"E:\Mind+\Arduino\arduino-builder\arduino-builder.exe",
            "arduino": r"E:\Mind+\Arduino",
        }
        sketch = Path(r"C:\tmp\blink\blink.ino")
        command = self.bridge.build_compile_command(
            context, sketch, Path(r"C:\tmp\build")
        )

        joined = " ".join(command)
        self.assertIn("-fqbn=arduino:avr:nano:cpu=atmega328", joined)
        self.assertIn("-compile", command)

    def test_upload_does_not_fallback_bootloader_on_unrelated_error(self):
        calls = []

        def runner(command, timeout=180):
            calls.append(command)
            return {"returncode": 1, "stdout": "", "stderr": "ser_open(): can't open device"}

        result = self.bridge.run_upload_attempts(
            avrdude=r"C:\avrdude.exe",
            config=r"C:\avrdude.conf",
            hex_file=Path(r"C:\blink.hex"),
            port="COM7",
            runner=runner,
        )

        self.assertEqual(len(calls), 1)
        self.assertFalse(result["success"])
        self.assertEqual(result["diagnostics"]["error_type"], "serial_port_unavailable")

    def test_upload_tries_115200_only_after_sync_failure_at_57600(self):
        calls = []

        def runner(command, timeout=180):
            calls.append(command)
            baud = command[command.index("-b") + 1]
            if baud == "57600":
                return {"returncode": 1, "stdout": "", "stderr": "avrdude: stk500_getsync(): not in sync"}
            return {
                "returncode": 0,
                "stdout": "avrdude done.  Thank you.",
                "stderr": "bytes of flash verified",
            }

        result = self.bridge.run_upload_attempts(
            avrdude=r"C:\avrdude.exe",
            config=r"C:\avrdude.conf",
            hex_file=Path(r"C:\blink.hex"),
            port="COM7",
            runner=runner,
        )

        self.assertEqual(len(calls), 2)
        self.assertTrue(result["success"])
        self.assertEqual(result["baud"], 115200)
        self.assertEqual(result["bootloader_profile"], "new_bootloader_compatible")

    def test_upload_result_does_not_invoke_avrdude_when_multiple_wired_ports_are_ambiguous(self):
        with tempfile.TemporaryDirectory() as temporary:
            hex_file = Path(temporary) / "demo.hex"
            hex_file.write_bytes(b"compiled")
            calls = {"find": 0, "upload": 0}
            original_scan_ports = self.bridge.scan_ports
            original_find_avrdude = self.bridge._find_avrdude
            original_run_upload_attempts = self.bridge.run_upload_attempts
            self.bridge.scan_ports = lambda: [
                {
                    "address": "COM5",
                    "is_bluetooth": False,
                    "nano_likely": False,
                    "eligible_for_upload": True,
                },
                {
                    "address": "COM6",
                    "is_bluetooth": False,
                    "nano_likely": False,
                    "eligible_for_upload": True,
                },
            ]
            def unexpected_find_avrdude(context):
                calls["find"] += 1
                raise AssertionError("_find_avrdude should not run when port selection is ambiguous")

            def unexpected_upload_attempts(**kwargs):
                calls["upload"] += 1
                raise AssertionError("run_upload_attempts should not run when port selection is ambiguous")

            self.bridge._find_avrdude = unexpected_find_avrdude
            self.bridge.run_upload_attempts = unexpected_upload_attempts
            try:
                result = self.bridge.upload_result(
                    {"backend": "mindplus-2-cli"},
                    {},
                    {"application_hex": str(hex_file)},
                )
            finally:
                self.bridge.scan_ports = original_scan_ports
                self.bridge._find_avrdude = original_find_avrdude
                self.bridge.run_upload_attempts = original_run_upload_attempts

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "multiple_wired_ports_require_selection")
        self.assertFalse(result["upload_executed"])
        self.assertEqual(calls, {"find": 0, "upload": 0})

    def test_upload_result_does_not_invoke_avrdude_for_explicit_bluetooth_port(self):
        with tempfile.TemporaryDirectory() as temporary:
            hex_file = Path(temporary) / "demo.hex"
            hex_file.write_bytes(b"compiled")
            calls = {"find": 0, "upload": 0}
            original_scan_ports = self.bridge.scan_ports
            original_find_avrdude = self.bridge._find_avrdude
            original_run_upload_attempts = self.bridge.run_upload_attempts
            self.bridge.scan_ports = lambda: [
                {
                    "address": "COM3",
                    "is_bluetooth": True,
                    "nano_likely": False,
                    "eligible_for_upload": False,
                },
                {
                    "address": "COM7",
                    "is_bluetooth": False,
                    "nano_likely": True,
                    "eligible_for_upload": True,
                },
            ]
            def unexpected_find_avrdude(context):
                calls["find"] += 1
                raise AssertionError("_find_avrdude should not run for an explicit Bluetooth port")

            def unexpected_upload_attempts(**kwargs):
                calls["upload"] += 1
                raise AssertionError("run_upload_attempts should not run for an explicit Bluetooth port")

            self.bridge._find_avrdude = unexpected_find_avrdude
            self.bridge.run_upload_attempts = unexpected_upload_attempts
            try:
                result = self.bridge.upload_result(
                    {"backend": "mindplus-2-cli"},
                    {"port": "COM3"},
                    {"application_hex": str(hex_file)},
                )
            finally:
                self.bridge.scan_ports = original_scan_ports
                self.bridge._find_avrdude = original_find_avrdude
                self.bridge.run_upload_attempts = original_run_upload_attempts

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "bluetooth_port_rejected")
        self.assertFalse(result["upload_executed"])
        self.assertEqual(calls, {"find": 0, "upload": 0})

    def test_compile_upload_stops_before_upload_when_compile_fails(self):
        called = {"upload": False}

        def compile_fn(context, request):
            return {"success": False, "error": "compile_failed"}

        def upload_fn(context, request, compiled):
            called["upload"] = True
            return {"success": True}

        result = self.bridge.compile_upload_result(
            {}, {"code": "bad"}, compile_fn=compile_fn, upload_fn=upload_fn
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["stage"], "compile")
        self.assertFalse(called["upload"])

    def test_compile_upload_automatically_uploads_after_compile(self):
        called = {"upload": False}

        def compile_fn(context, request):
            return {"success": True, "application_hex": r"C:\build\demo.hex"}

        def upload_fn(context, request, compiled):
            called["upload"] = True
            return {
                "success": True,
                "upload_executed": True,
                "firmware_written": True,
                "port": "COM8",
            }

        result = self.bridge.compile_upload_result(
            {}, {"code": "void setup(){} void loop(){}"},
            compile_fn=compile_fn, upload_fn=upload_fn,
        )

        self.assertTrue(called["upload"])
        self.assertTrue(result["success"])
        self.assertTrue(result["automatic_upload"])
        self.assertTrue(result["hardware_detected"])
        self.assertEqual(result["stage"], "complete")

    def test_compile_upload_prompts_for_connection_when_hardware_is_missing(self):
        def compile_fn(context, request):
            return {"success": True, "application_hex": r"C:\build\demo.hex"}

        def upload_fn(context, request, compiled):
            return {
                "success": False,
                "error": "no_wired_upload_port_found",
                "upload_executed": False,
                "ports": [],
            }

        result = self.bridge.compile_upload_result(
            {}, {"code": "void setup(){} void loop(){}"},
            compile_fn=compile_fn, upload_fn=upload_fn,
        )

        self.assertFalse(result["success"])
        self.assertTrue(result["automatic_upload"])
        self.assertFalse(result["hardware_detected"])
        self.assertTrue(result["hardware_connection_required"])
        self.assertTrue(result["retry_when_hardware_connected"])
        self.assertEqual(result["stage"], "awaiting-hardware")
        self.assertIn("接入", result["teacher_message"])

    def test_compile_failure_is_marked_for_bounded_code_repair(self):
        def compile_fn(context, request):
            return {"success": False, "error": "compile_failed"}

        result = self.bridge.compile_upload_result(
            {}, {"code": "bad"}, compile_fn=compile_fn,
        )

        self.assertTrue(result["auto_repair_recommended"])
        self.assertEqual(result["repair_scope"], "code")
        self.assertEqual(result["max_agent_repair_attempts"], 2)
        self.assertIn("修改", result["teacher_message"])

    def test_installer_refuses_download_when_any_mindplus_exists(self):
        result = self.bridge.prepare_environment(
            installations=[{"backend": "mindplus-2-cli", "toolchain_present": True}],
            system={"os_family": "windows", "architecture": "x86_64", "distribution": "windows"},
            execute_download=False,
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "existing_mindplus_reused")
        self.assertFalse(result["download_executed"])

    def test_installer_only_auto_downloads_allowlisted_official_url(self):
        safe = self.bridge.download_policy(
            "https://download3.dfrobot.com.cn/MindPlus_Win_V1.8.1_RC3.0.exe"
        )
        unsafe = self.bridge.download_policy("https://example.com/MindPlus.exe")

        self.assertTrue(safe["allowed"])
        self.assertFalse(unsafe["allowed"])

    def test_environment_prepare_returns_manual_route_for_unconfirmed_arch(self):
        result = self.bridge.prepare_environment(
            installations=[],
            system={"os_family": "windows", "architecture": "arm64", "distribution": "windows"},
            execute_download=True,
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "compatibility_confirmation_required")
        self.assertFalse(result["download_executed"])

    def test_installer_launch_requires_explicit_request_and_existing_file(self):
        calls = []

        def launcher(path):
            calls.append(path)
            return {"success": True, "process_started": True}

        with tempfile.TemporaryDirectory() as temporary:
            installer = Path(temporary) / "MindPlus.exe"
            missing = self.bridge.launch_installer(installer, launcher=launcher)
            installer.write_bytes(b"MZ-test")
            started = self.bridge.launch_installer(installer, launcher=launcher)

        self.assertFalse(missing["success"])
        self.assertEqual(missing["error"], "installer_file_not_found")
        self.assertTrue(started["success"])
        self.assertEqual(len(calls), 1)

    def test_existing_mindplus_blocks_install_launch(self):
        result = self.bridge.prepare_environment(
            installations=[{"backend": "mindplus-1-builder", "toolchain_present": True}],
            system={"os_family": "windows", "architecture": "x86_64", "distribution": "windows"},
            execute_download=True,
            launch_after_download=True,
        )

        self.assertEqual(result["status"], "existing_mindplus_reused")
        self.assertFalse(result["download_executed"])
        self.assertFalse(result.get("installer_started", False))


if __name__ == "__main__":
    unittest.main()
