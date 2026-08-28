from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from chatmaker.installers import downloads


ROOT = Path(__file__).resolve().parents[2]


class DomesticRuntimeTests(unittest.TestCase):
    def test_runtime_registry_puts_domestic_sources_before_official_fallbacks(self):
        registry = downloads.load_runtime_sources()
        self.assertEqual(registry["policy"], "domestic-first")
        python = downloads.runtime_artifact("python")
        node = downloads.runtime_artifact("node")
        self.assertEqual(python["version"], "3.11.10")
        self.assertEqual(node["version"], "22.22.0")
        self.assertEqual(python["sources"][0]["kind"], "domestic_mirror")
        self.assertEqual(node["sources"][0]["kind"], "domestic_mirror")
        self.assertEqual(python["sources"][-1]["kind"], "official_fallback")
        self.assertEqual(node["sources"][-1]["kind"], "official_fallback")
        self.assertTrue(all(len(item["sha256"]) == 64 for item in (python, node)))
        self.assertEqual(downloads.package_sources("pip_indexes")[0]["id"], "aliyun-pypi")
        self.assertEqual(downloads.package_sources("npm_registries")[0]["id"], "npmmirror-npm")

    def test_hash_mismatch_on_domestic_source_falls_back_to_official_bytes(self):
        expected = b"trusted-runtime"
        artifact = {
            "filename": "runtime.bin",
            "size": len(expected),
            "sha256": hashlib.sha256(expected).hexdigest(),
            "sources": [
                {"id": "cn", "kind": "domestic_mirror", "url": "https://cn.example/runtime.bin"},
                {"id": "official", "kind": "official_fallback", "url": "https://official.example/runtime.bin"},
            ],
        }
        calls: list[str] = []

        def fetcher(url, destination, *, timeout, max_bytes):
            calls.append(url)
            destination.write_bytes(b"wrong-runtime" if "cn.example" in url else expected)

        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "runtime.bin"
            receipt = downloads.download_locked(artifact, destination, fetcher=fetcher)
            self.assertEqual(destination.read_bytes(), expected)

        self.assertEqual(calls, [artifact["sources"][0]["url"], artifact["sources"][1]["url"]])
        self.assertEqual(receipt.source_id, "official")
        self.assertEqual(receipt.attempted_source_ids, ("cn", "official"))

    def test_configured_domestic_mirror_is_tried_before_built_in_sources(self):
        expected = b"configured"
        artifact = {
            "filename": "runtime.bin",
            "size": len(expected),
            "sha256": hashlib.sha256(expected).hexdigest(),
            "sources": [
                {"id": "official", "kind": "official_fallback", "url": "https://official.example/runtime.bin"},
            ],
        }
        calls: list[str] = []

        def fetcher(url, destination, *, timeout, max_bytes):
            calls.append(url)
            destination.write_bytes(expected)

        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(
            os.environ, {"CHATMAKER_DOWNLOAD_MIRROR_BASE": "https://mirror.example/chatmaker"}
        ):
            receipt = downloads.download_locked(
                artifact, Path(directory) / "runtime.bin", fetcher=fetcher
            )

        self.assertEqual(calls, ["https://mirror.example/chatmaker/runtime.bin"])
        self.assertEqual(receipt.source_id, "configured-domestic-mirror")

    def test_powershell_check_only_reports_plan_without_creating_runtime(self):
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if not powershell:
            self.skipTest("PowerShell unavailable")
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "runtime"
            completed = subprocess.run(
                [
                    powershell,
                    "-NoProfile",
                    "-File",
                    str(ROOT / "scripts/setup_local_runtime.ps1"),
                    "-SourceRoot",
                    str(ROOT),
                    "-RuntimeRoot",
                    str(runtime),
                    "-CheckOnly",
                ],
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            value = json.loads(completed.stdout.strip())
            self.assertTrue(value["success"])
            self.assertEqual(value["status"], "plan")
            self.assertEqual(value["pip_indexes"][0]["id"], "aliyun-pypi")
            self.assertFalse(value["global_path_modified"])
            self.assertFalse(runtime.exists())

    def test_powershell_check_only_recognizes_offline_core_layout(self):
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if not powershell:
            self.skipTest("PowerShell unavailable")
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "core"
            registry = source / "runtime/chatmaker/installers/runtime_sources.json"
            registry.parent.mkdir(parents=True)
            registry.write_bytes(downloads.SOURCE_REGISTRY.read_bytes())
            wheelhouse = source / "core-runtime/wheelhouse"
            wheelhouse.mkdir(parents=True)
            (source / "core-runtime/requirements.txt").write_text("example==1 --hash=sha256:" + "0" * 64 + "\n", encoding="ascii")
            runtime = Path(directory) / "runtime"
            completed = subprocess.run(
                [
                    powershell,
                    "-NoProfile",
                    "-File",
                    str(ROOT / "scripts/setup_local_runtime.ps1"),
                    "-SourceRoot",
                    str(source),
                    "-RuntimeRoot",
                    str(runtime),
                    "-CheckOnly",
                ],
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            value = json.loads(completed.stdout.strip())
            self.assertEqual(value["package_mode"], "offline-core-wheelhouse")
            self.assertFalse(runtime.exists())

    def test_release_lock_contains_the_runtime_font_dependency(self):
        lines = (ROOT / "distribution/core-runtime/requirements.lock").read_text(
            encoding="utf-8"
        ).splitlines()
        self.assertIn("fonttools==4.63.0", lines)


if __name__ == "__main__":
    unittest.main()
