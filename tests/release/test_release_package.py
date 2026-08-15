from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import tomllib
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RELEASE_VERSION = "0.1.0-rc5"


def load_builder():
    path = ROOT / "scripts" / "build_release.py"
    spec = importlib.util.spec_from_file_location("chatmaker_build_release", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ReleasePackageTests(unittest.TestCase):
    def test_checked_in_registry_is_signed_and_pins_the_exact_pack_artifacts(self):
        sys.path.insert(0, str(ROOT / "runtime"))
        from chatmaker.installers.registry import verify_registry

        registry_path = ROOT / "distribution" / "registry" / "registry.json"
        signature_path = ROOT / "distribution" / "registry" / "registry.sig.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        expected = {
            "chatmaker-board-arduino-nano-classic-wiki": (
                "chatmaker-board-arduino-nano-classic-wiki-1.0.0.cmpack",
                10463,
                "f436a6c149b9d9627f34257400854be138143d34cf928e6547a33c4366bde30a",
            ),
            "chatmaker-board-arduino-uno-r3-wiki": (
                "chatmaker-board-arduino-uno-r3-wiki-1.0.0.cmpack",
                10291,
                "67110bf2e13d5ba7a9cc00235897c135ed3ee80208991d303b19330d2250a2c6",
            ),
            "chatmaker-board-esp32-devkit-v1-wiki": (
                "chatmaker-board-esp32-devkit-v1-wiki-1.0.0.cmpack",
                10471,
                "9cbf789ecf0598c24c9a5a238e7842366d2834c01f53887be338c8224579b34d",
            ),
        }
        self.assertEqual(registry["sequence"], 1)
        generated_at = datetime.fromisoformat(registry["generated_at"].replace("Z", "+00:00"))
        expires_at = datetime.fromisoformat(registry["expires_at"].replace("Z", "+00:00"))
        self.assertLessEqual((expires_at - generated_at).days, 31)
        self.assertEqual(len(registry["packs"]), 3)
        for item in registry["packs"]:
            filename, length, digest = expected[item["pack_id"]]
            artifact = ROOT / "distribution" / "packs" / filename
            self.assertEqual(item["url"], (
                "https://raw.githubusercontent.com/Amasun93/ChatMaker/"
                "25ad1df2376872e81b3fe1025420cf3f76376719/distribution/packs/"
                + filename
            ))
            self.assertEqual(item["length"], artifact.stat().st_size)
            self.assertEqual(item["length"], length)
            self.assertEqual(hashlib.sha256(artifact.read_bytes()).hexdigest(), digest)
            self.assertEqual(item["sha256"], digest)

        with tempfile.TemporaryDirectory() as directory:
            verified = verify_registry(
                registry_path.read_bytes(),
                signature_path.read_bytes(),
                registry_url=(
                    "https://raw.githubusercontent.com/Amasun93/ChatMaker/main/"
                    "distribution/registry/registry.json"
                ),
                state_path=Path(directory) / "state.json",
                now=datetime(2026, 8, 16, 12, tzinfo=timezone.utc),
            )
        self.assertEqual(verified["key_id"], "chatmaker-official-2026-01")
        self.assertEqual(verified["sequence"], 1)

    def test_core_excludes_knowledge_source_workspace_even_if_recursively_included(self):
        builder = load_builder()
        with tempfile.TemporaryDirectory() as directory:
            result = builder.build_release(ROOT, Path(directory), RELEASE_VERSION)
            with zipfile.ZipFile(result["archive"]) as archive:
                names = set(archive.namelist())

        prefix = f"ChatMaker-Core-{RELEASE_VERSION}/"
        self.assertFalse(any("knowledge_sources/" in name for name in names), names)

    def test_core_readme_relative_links_resolve_inside_core(self):
        builder = load_builder()
        with tempfile.TemporaryDirectory() as directory:
            result = builder.build_release(ROOT, Path(directory), RELEASE_VERSION)
            prefix = f"ChatMaker-Core-{RELEASE_VERSION}/"
            with zipfile.ZipFile(result["archive"]) as archive:
                names = set(archive.namelist())
                for readme_name in ("README.md", "README_EN.md"):
                    text = archive.read(prefix + readme_name).decode("utf-8")
                    for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
                        if target.startswith(("https://", "http://", "#", "mailto:")):
                            continue
                        relative = target.split("#", 1)[0].replace("\\", "/")
                        self.assertIn(
                            prefix + relative,
                            names,
                            f"{readme_name} links to a file excluded from Core: {target}",
                        )

    def test_release_zip_excludes_esp32_runtime_cache_directories(self):
        builder = load_builder()
        with tempfile.TemporaryDirectory() as directory:
            result = builder.build_release(ROOT, Path(directory), RELEASE_VERSION)
            with zipfile.ZipFile(result["archive"]) as archive:
                names = set(archive.namelist())

        prefix = f"ChatMaker-Core-{RELEASE_VERSION}/examples/chatduino/esp32/"
        self.assertIn(prefix + "blink-external-led/blink-external-led.ino", names)
        self.assertFalse(
            any(
                cache_part in Path(name).parts
                for name in names
                for cache_part in (
                    ".chatmaker-esp32-builds",
                    ".chatmaker-esp32-cache",
                )
            ),
            names,
        )

    def test_rc5_verification_records_timeout_before_corrected_final_success(self):
        verification = (
            ROOT / "docs" / "verification" / "2026-08-15-rc5-release-candidate.md"
        ).read_text(encoding="utf-8")

        timeout_position = verification.find("900 秒默认预算下超时")
        correction_position = verification.find("编译默认预算修正为 1200 秒")
        success_position = verification.find("1056.41 秒")

        self.assertGreaterEqual(timeout_position, 0)
        self.assertGreaterEqual(correction_position, 0)
        self.assertGreaterEqual(success_position, 0)
        self.assertLess(timeout_position, correction_position)
        self.assertLess(correction_position, success_position)
        self.assertIn("946528 B", verification)
        self.assertIn("47168 B", verification)
        self.assertNotIn("Fix round 1 修正文档后重新生成最终归档", verification)
        self.assertNotIn("chatmaker-rc5-fix1-final-", verification)

    def test_rc5_verification_records_latest_final_extraction_metrics(self):
        verification = (
            ROOT / "docs" / "verification" / "2026-08-15-rc5-release-candidate.md"
        ).read_text(encoding="utf-8")

        final_position = verification.find("最新最终归档的全新解压复验")

        self.assertGreaterEqual(final_position, 0)
        final_evidence = verification[final_position:]
        self.assertIn("220.876 秒", final_evidence)
        self.assertIn("904.292 秒", final_evidence)
        self.assertIn("946528 B", final_evidence)
        self.assertIn("47168 B", final_evidence)

    def test_installation_verifies_archive_before_entering_extracted_directory(self):
        installation = (ROOT / "docs" / "installation.md").read_text(encoding="utf-8")
        checksum_position = installation.find("Get-FileHash .\\ChatMaker-0.1.0-rc5.zip")
        extract_position = installation.find("Expand-Archive .\\ChatMaker-0.1.0-rc5.zip")
        enter_position = installation.find("Set-Location .\\ChatMaker-0.1.0-rc5")

        self.assertGreaterEqual(checksum_position, 0)
        self.assertGreaterEqual(extract_position, 0)
        self.assertGreaterEqual(enter_position, 0)
        self.assertLess(checksum_position, extract_position)
        self.assertLess(extract_position, enter_position)

    def test_workbuddy_stdio_is_excluded_from_help_claim(self):
        installation = (ROOT / "docs" / "installation.md").read_text(encoding="utf-8")

        self.assertNotIn("所有已安装命令均支持 `--help`", installation)
        self.assertNotIn("All installed commands support `--help`", installation)
        self.assertNotRegex(installation, r"chatmaker-workbuddy-mcp\s+--help")
        self.assertIn('"method":"tools/list"', installation)

    def test_core_cli_defaults_to_rc5_and_reports_archive_size(self):
        with tempfile.TemporaryDirectory() as directory:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_release.py"),
                    "--root",
                    str(ROOT),
                    "--output",
                    directory,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=True,
            )
            result = json.loads(completed.stdout)
            archive_size = Path(result["archive"]).stat().st_size

        self.assertEqual(result["version"], RELEASE_VERSION)
        self.assertEqual(
            Path(result["archive"]).name,
            f"ChatMaker-Core-{RELEASE_VERSION}.zip",
        )
        self.assertEqual(result["size_bytes"], archive_size)

    def test_core_zip_is_deterministic_and_matches_the_frozen_content_classes(self):
        builder = load_builder()
        with tempfile.TemporaryDirectory() as directory:
            first = builder.build_release(ROOT, Path(directory) / "first", RELEASE_VERSION)
            second = builder.build_release(ROOT, Path(directory) / "second", RELEASE_VERSION)

            first_zip = Path(first["archive"])
            second_zip = Path(second["archive"])
            first_hash = hashlib.sha256(first_zip.read_bytes()).hexdigest()
            second_hash = hashlib.sha256(second_zip.read_bytes()).hexdigest()
            with zipfile.ZipFile(first_zip) as archive:
                names = set(archive.namelist())

        prefix = f"ChatMaker-Core-{RELEASE_VERSION}/"
        metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(metadata["project"]["version"], "0.1.0rc5")
        self.assertEqual(first_hash, second_hash)
        self.assertEqual(first_hash, first["sha256"])
        root_files = {
            name.removeprefix(prefix)
            for name in names
            if name.startswith(prefix)
            and "/" not in name.removeprefix(prefix)
        }
        self.assertEqual(
            root_files,
            {"LICENSE", "README.md", "README_EN.md", "pyproject.toml"},
        )
        docs_files = {
            name.removeprefix(prefix)
            for name in names
            if name.startswith(prefix + "docs/")
        }
        self.assertEqual(docs_files, {"docs/installation.md"})
        self.assertIn(prefix + "skills/chatmaker/SKILL.md", names)
        self.assertIn(prefix + "skills/chatduino/SKILL.md", names)
        self.assertIn(prefix + "skills/chatweb/SKILL.md", names)
        self.assertIn(prefix + "runtime/chatmaker/installers/codex.py", names)
        self.assertIn(prefix + "runtime/chatmaker/installers/workbuddy.py", names)
        self.assertIn(prefix + "runtime/chatmaker/installers/skill_bundle.py", names)
        self.assertIn(prefix + "runtime/chatmaker/hardware/esp32_devkit_v1.py", names)
        self.assertIn(prefix + "runtime/chatmaker/route.py", names)
        self.assertIn(prefix + "runtime/chatmaker/web/embed.py", names)
        self.assertIn(prefix + "runtime/chatmaker/web/planner.py", names)
        self.assertIn(prefix + "runtime/chatmaker/web/playground.py", names)
        self.assertIn(prefix + "examples/chatduino/esp32/ap-led-sensor/ap-led-sensor.ino", names)
        self.assertIn(prefix + "examples/chatduino/esp32/ap-led-sensor/page_html.h", names)
        self.assertIn(prefix + "examples/chatweb/esp32-ap-control.html", names)
        self.assertIn(prefix + "examples/chatweb/advanced-playground.html", names)
        self.assertIn(prefix + "packs/llmwiki/boards/arduino-nano-classic.yaml", names)
        self.assertIn(prefix + "packs/schemas/registry.schema.json", names)
        self.assertEqual(
            len([name for name in names if name.startswith(prefix + "packs/boards/")]),
            3,
        )
        self.assertEqual(
            len([name for name in names if name.startswith(prefix + "packs/components/")]),
            12,
        )
        self.assertEqual(
            len([name for name in names if name.startswith(prefix + "packs/recipes/")]),
            14,
        )
        self.assertEqual(
            len([name for name in names if name.startswith(prefix + "packs/llmwiki/boards/")]),
            3,
        )
        forbidden_parts = {
            ".git",
            ".github",
            "__pycache__",
            "tests",
            "knowledge_sources",
            "distribution",
            "node_modules",
        }
        self.assertFalse(
            any(forbidden_parts.intersection(Path(name).parts) for name in names),
            names,
        )
        self.assertFalse(any(name.endswith(".cmpack") for name in names), names)
        self.assertFalse(any("llmwiki/boards/" in name and name.endswith(".md") for name in names))


if __name__ == "__main__":
    unittest.main()
