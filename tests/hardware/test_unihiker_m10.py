from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.hardware.unihiker_m10 import check_project, credential_help, execute_request


class UnihikerM10Tests(unittest.TestCase):
    def write_project(self, root: Path, source: str, *, requirements: bool = True) -> Path:
        root.mkdir(parents=True, exist_ok=True)
        (root / "main.py").write_text(source, encoding="utf-8")
        if requirements:
            (root / "requirements.txt").write_text("# board-provided packages\n", encoding="utf-8")
        return root

    def test_board_record_keeps_m10_and_k10_separate(self):
        record = yaml.safe_load(
            (ROOT / "packs" / "boards" / "unihiker-m10.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(record["id"], "unihiker-m10")
        self.assertEqual(record["family"], "linux-sbc")
        self.assertEqual(record["identity"]["model"], "UNIHIKER M10")
        self.assertIn("UNIHIKER K10", record["identity"]["forbidden_aliases"])
        self.assertEqual(record["verification"]["firmware_uploaded"]["status"], "not_applicable")

    def test_checked_in_example_passes_static_preflight(self):
        project = ROOT / "examples" / "chatduino" / "unihiker-m10" / "hello-status"
        result = check_project(project)
        self.assertTrue(result["success"], result)
        self.assertEqual(result["stage"], "source_checked")
        self.assertEqual(result["board_execution"], "unverified")

    def test_rejects_python_newer_than_37_and_embedded_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            project = self.write_project(
                Path(directory),
                'API_TOKEN = "real-value"\nmatch 1:\n    case 1:\n        pass\n',
            )
            result = check_project(project)
        self.assertFalse(result["success"])
        self.assertEqual(result["issues"][0]["code"], "python37_syntax")

        with tempfile.TemporaryDirectory() as directory:
            project = self.write_project(Path(directory), 'API_TOKEN = "real-value"\n')
            result = check_project(project)
        self.assertFalse(result["success"])
        self.assertIn("embedded_secret", {item["code"] for item in result["issues"]})

    def test_known_provider_secret_returns_exact_replacement_help(self):
        with tempfile.TemporaryDirectory() as directory:
            project = self.write_project(
                Path(directory), 'DASHSCOPE_API_KEY = "internal-project-value"\n'
            )
            result = check_project(project)

        self.assertFalse(result["success"])
        self.assertEqual(len(result["credential_help"]), 1)
        help_result = result["credential_help"][0]
        self.assertEqual(help_result["provider"], "aliyun-dashscope")
        self.assertEqual(help_result["fields"], ["aliyun.dashscope.api_key"])
        self.assertEqual(
            help_result["obtain_url"],
            "https://bailian.console.aliyun.com/cn-beijing#/api-key",
        )
        self.assertFalse(help_result["share_secret_with_chat"])

    def test_credential_help_covers_each_supported_provider_without_secret_values(self):
        providers = {
            "aliyun-dashscope",
            "aliyun-qwen-omni",
            "volcengine-ark",
            "volcengine-openspeech",
            "baidu-tts",
        }
        for provider in providers:
            with self.subTest(provider=provider):
                result = credential_help(provider)
                self.assertTrue(result["success"], result)
                self.assertTrue(result["fields"])
                self.assertEqual(result["public_example_value"], "")
                self.assertTrue(result["obtain_url"].startswith("https://"))
                self.assertFalse(result["share_secret_with_chat"])
                self.assertIn("teacher-controlled proxy", result["shared_device_risk"])

        unknown = credential_help("unknown-provider")
        self.assertFalse(unknown["success"])
        self.assertEqual(set(unknown["supported_providers"]), providers)

    def test_camera_cleanup_is_required_and_desktop_ui_is_only_a_warning(self):
        source = "import cv2\ncamera = cv2.VideoCapture(0)\ncv2.imshow('x', frame)\n"
        with tempfile.TemporaryDirectory() as directory:
            result = check_project(self.write_project(Path(directory), source))
        codes = {item["code"]: item["level"] for item in result["issues"]}
        self.assertEqual(codes["desktop_ui"], "warning")
        self.assertEqual(codes["camera_not_released"], "error")
        self.assertFalse(result["success"])

    def test_structured_request_and_cli_use_the_same_contract(self):
        project = ROOT / "examples" / "chatduino" / "unihiker-m10" / "hello-status"
        direct = execute_request({"action": "check_project", "project": str(project)})
        self.assertTrue(direct["success"], direct)

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "chatmaker.hardware.unihiker_m10",
                "--request-json",
                json.dumps({"action": "check_project", "project": str(project)}),
            ],
            cwd=ROOT,
            env={**dict(__import__("os").environ), "PYTHONPATH": str(ROOT / "runtime")},
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(json.loads(completed.stdout)["success"])


if __name__ == "__main__":
    unittest.main()
