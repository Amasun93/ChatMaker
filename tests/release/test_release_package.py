from __future__ import annotations

import base64
import csv
import hashlib
import importlib.util
import io
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

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


ROOT = Path(__file__).resolve().parents[2]
RELEASE_VERSION = "0.1.0-rc5"
TEST_PLATFORM = "windows-amd64"


def load_builder():
    path = ROOT / "scripts" / "build_release.py"
    spec = importlib.util.spec_from_file_location("chatmaker_build_release", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def prepared_runtime(directory: Path) -> Path:
    root = directory / "prepared"
    wheelhouse = root / "wheelhouse"
    wheelhouse.mkdir(parents=True, exist_ok=True)
    wheel = wheelhouse / "chatmaker-0.1.0rc5-py3-none-any.whl"
    payloads = {
        "chatmaker/__init__.py": b"",
        "chatmaker-0.1.0rc5.dist-info/METADATA": b"Metadata-Version: 2.1\nName: chatmaker\nVersion: 0.1.0rc5\n",
        "chatmaker-0.1.0rc5.dist-info/WHEEL": b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
    }
    rows: list[list[str]] = []
    for name, value in sorted(payloads.items()):
        encoded = base64.urlsafe_b64encode(hashlib.sha256(value).digest()).rstrip(b"=").decode("ascii")
        rows.append([name, f"sha256={encoded}", str(len(value))])
    rows.append(["chatmaker-0.1.0rc5.dist-info/RECORD", "", ""])
    record = io.StringIO(newline="")
    csv.writer(record, lineterminator="\n").writerows(rows)
    def frozen_wheel_info(name: str) -> zipfile.ZipInfo:
        info = zipfile.ZipInfo(name, date_time=(2026, 8, 14, 0, 0, 0))
        info.create_system = 3
        info.external_attr = 0o100644 << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        return info

    with zipfile.ZipFile(wheel, "w") as archive:
        for name, value in payloads.items():
            archive.writestr(frozen_wheel_info(name), value)
        archive.writestr(
            frozen_wheel_info("chatmaker-0.1.0rc5.dist-info/RECORD"),
            record.getvalue(),
        )
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    manifest = {
        "schema_version": 2,
        "platform_tag": TEST_PLATFORM,
        "python_requires": "==3.11.*",
        "core_wheel": wheel.name,
        "wheels": [{"filename": wheel.name, "project": "chatmaker", "version": "0.1.0rc5", "size": wheel.stat().st_size, "sha256": digest, "tags": ["py3-none-any"], "requires": []}],
    }
    (root / "manifest.json").write_bytes((json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii"))
    (root / "requirements.txt").write_bytes(f"chatmaker==0.1.0rc5 --hash=sha256:{digest}\n".encode("ascii"))
    return root


class ReleasePackageTests(unittest.TestCase):
    def test_checked_in_registry_is_signed_and_pins_the_exact_pack_artifacts(self):
        registry_path = ROOT / "distribution" / "registry" / "registry.json"
        signature_path = ROOT / "distribution" / "registry" / "registry.sig.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        expected = {
            "chatmaker-board-arduino-nano-classic-knowledge": (
                "chatmaker-board-arduino-nano-classic-knowledge-1.2.0.cmpack",
                11785,
                "c836cb390eaecc7c632d45722900e301499a19682aeab4a5357b359b357bcf20",
            ),
            "chatmaker-board-arduino-uno-r3-knowledge": (
                "chatmaker-board-arduino-uno-r3-knowledge-1.2.0.cmpack",
                11244,
                "f925ccbd7f91fe7fd0e665adb720b91f22db46c50f63358e352735c9f3b93713",
            ),
            "chatmaker-board-esp32-devkit-v1-knowledge": (
                "chatmaker-board-esp32-devkit-v1-knowledge-1.2.0.cmpack",
                11621,
                "c02249952c827244ce1273f20760a36d266ab17ecc7bd87ef67a8cc4a1fc8a2c",
            ),
            "chatmaker-board-idmc-0001-starcore-v4-2-2-knowledge": (
                "chatmaker-board-idmc-0001-starcore-v4-2-2-knowledge-1.2.0.cmpack",
                16843,
                "22a56bce05affd1584664ee4b95752105e71600a10cc66e82e757d519b2996c0",
            ),
        }
        self.assertEqual(registry["sequence"], 4)
        generated_at = datetime.fromisoformat(registry["generated_at"].replace("Z", "+00:00"))
        expires_at = datetime.fromisoformat(registry["expires_at"].replace("Z", "+00:00"))
        self.assertLessEqual((expires_at - generated_at).days, 31)
        self.assertEqual(len(registry["packs"]), 4)
        for item in registry["packs"]:
            filename, length, digest = expected[item["pack_id"]]
            artifact = ROOT / "distribution" / "packs" / filename
            pinned_commit = (
                "ea19a1a3d3f47f6e0768df0473a6b55d6126c63c"
                if item["board_id"] == "idmc-0001-starcore-v4-2-2"
                else "1556a055d9625409e9380f4e6abdf7c0e95778fc"
            )
            self.assertEqual(item["url"], (
                "https://raw.githubusercontent.com/Amasun93/ChatMaker/"
                + pinned_commit
                + "/distribution/packs/"
                + filename
            ))
            self.assertEqual(item["length"], artifact.stat().st_size)
            self.assertEqual(item["length"], length)
            self.assertEqual(hashlib.sha256(artifact.read_bytes()).hexdigest(), digest)
            self.assertEqual(item["sha256"], digest)

        detached = json.loads(signature_path.read_text(encoding="utf-8"))
        anchors = json.loads(
            (ROOT / "runtime" / "chatmaker" / "trust" / "official_registry_keys.json").read_text(
                encoding="utf-8"
            )
        )
        key = next(item for item in anchors["keys"] if item["key_id"] == detached["key_id"])
        Ed25519PublicKey.from_public_bytes(
            base64.b64decode(key["public_key_base64"], validate=True)
        ).verify(
            base64.b64decode(detached["signature"], validate=True),
            registry_path.read_bytes(),
        )
        self.assertEqual(detached["key_id"], "chatmaker-official-2026-01")

    def test_core_excludes_knowledge_source_workspace_even_if_recursively_included(self):
        builder = load_builder()
        with tempfile.TemporaryDirectory() as directory:
            result = builder.build_release(ROOT, Path(directory), RELEASE_VERSION, platform_tag=TEST_PLATFORM, prepared_root=prepared_runtime(Path(directory)))
            with zipfile.ZipFile(result["archive"]) as archive:
                names = set(archive.namelist())

        prefix = f"ChatMaker-Core-{RELEASE_VERSION}-{TEST_PLATFORM}/"
        self.assertFalse(any("knowledge_sources/" in name for name in names), names)

    def test_core_release_contains_the_stdlib_bootstrap_script(self):
        """Catches publishing a Core archive that cannot install itself on a fresh machine."""
        builder = load_builder()
        with tempfile.TemporaryDirectory() as directory:
            result = builder.build_release(ROOT, Path(directory), RELEASE_VERSION, platform_tag=TEST_PLATFORM, prepared_root=prepared_runtime(Path(directory)))
            with zipfile.ZipFile(result["archive"]) as archive:
                self.assertIn(
                    f"ChatMaker-Core-{RELEASE_VERSION}-{TEST_PLATFORM}/scripts/bootstrap.py",
                    archive.namelist(),
                )

    def test_core_readme_relative_links_resolve_inside_core(self):
        builder = load_builder()
        with tempfile.TemporaryDirectory() as directory:
            result = builder.build_release(ROOT, Path(directory), RELEASE_VERSION, platform_tag=TEST_PLATFORM, prepared_root=prepared_runtime(Path(directory)))
            prefix = f"ChatMaker-Core-{RELEASE_VERSION}-{TEST_PLATFORM}/"
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
            result = builder.build_release(ROOT, Path(directory), RELEASE_VERSION, platform_tag=TEST_PLATFORM, prepared_root=prepared_runtime(Path(directory)))
            with zipfile.ZipFile(result["archive"]) as archive:
                names = set(archive.namelist())

        prefix = f"ChatMaker-Core-{RELEASE_VERSION}-{TEST_PLATFORM}/examples/chatduino/esp32/"
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

    def test_installation_uses_a_trusted_bootstrap_and_all_detached_release_evidence(self):
        installation = (ROOT / "docs" / "installation.md").read_text(encoding="utf-8")
        checksum_position = installation.find("Get-FileHash .\\ChatMaker-Core-0.1.0-rc5-windows-amd64.zip")
        bootstrap_position = installation.find("python .\\trusted-bootstrap\\bootstrap.py", checksum_position)
        manifest_position = installation.find("--release-manifest", bootstrap_position)
        signature_position = installation.find("--release-signature", manifest_position)

        self.assertGreaterEqual(checksum_position, 0)
        self.assertGreaterEqual(bootstrap_position, 0)
        self.assertGreaterEqual(manifest_position, 0)
        self.assertGreaterEqual(signature_position, 0)
        self.assertLess(checksum_position, bootstrap_position)
        self.assertNotIn("Expand-Archive .\\ChatMaker-Core-0.1.0-rc5-windows-amd64.zip", installation)
        self.assertIn("point-in-time drift detection", installation)
        self.assertIn("not OS secure boot", installation)

    def test_workbuddy_stdio_is_excluded_from_help_claim(self):
        installation = (ROOT / "docs" / "installation.md").read_text(encoding="utf-8")

        self.assertNotIn("所有已安装命令均支持 `--help`", installation)
        self.assertNotIn("All installed commands support `--help`", installation)
        self.assertNotRegex(installation, r"chatmaker-workbuddy-mcp\s+--help")
        self.assertIn('"method":"tools/list"', installation)

    def test_core_cli_defaults_to_rc5_and_reports_archive_size(self):
        with tempfile.TemporaryDirectory() as directory:
            prepared = prepared_runtime(Path(directory))
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_release.py"),
                    "--root",
                    str(ROOT),
                    "--output",
                    directory,
                    "--platform-tag",
                    TEST_PLATFORM,
                    "--prepared-root",
                    str(prepared),
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
            f"ChatMaker-Core-{RELEASE_VERSION}-{TEST_PLATFORM}.zip",
        )
        self.assertEqual(result["size_bytes"], archive_size)

    def test_release_version_is_pep440_equal_to_the_core_wheel_version(self):
        """Catches punctuation stripping treating distinct PEP 440 versions as the same release."""
        builder = load_builder()
        with tempfile.TemporaryDirectory() as directory:
            prepared = prepared_runtime(Path(directory))
            with self.assertRaisesRegex(builder.ReleaseError, "core_wheel_version_mismatch"):
                builder.build_release(
                    ROOT,
                    Path(directory) / "dist",
                    "0.10-rc5",
                    platform_tag=TEST_PLATFORM,
                    prepared_root=prepared,
                )

    def test_core_zip_is_deterministic_and_matches_the_frozen_content_classes(self):
        builder = load_builder()
        with tempfile.TemporaryDirectory() as directory:
            first = builder.build_release(ROOT, Path(directory) / "first", RELEASE_VERSION, platform_tag=TEST_PLATFORM, prepared_root=prepared_runtime(Path(directory) / "fixture"))
            second = builder.build_release(ROOT, Path(directory) / "second", RELEASE_VERSION, platform_tag=TEST_PLATFORM, prepared_root=prepared_runtime(Path(directory) / "fixture"))

            first_zip = Path(first["archive"])
            second_zip = Path(second["archive"])
            first_hash = hashlib.sha256(first_zip.read_bytes()).hexdigest()
            second_hash = hashlib.sha256(second_zip.read_bytes()).hexdigest()
            with zipfile.ZipFile(first_zip) as archive:
                names = set(archive.namelist())
                infos = archive.infolist()

        prefix = f"ChatMaker-Core-{RELEASE_VERSION}-{TEST_PLATFORM}/"
        metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(metadata["project"]["version"], "0.1.0rc5")
        self.assertEqual(first_hash, second_hash)
        self.assertEqual(first_hash, first["sha256"])
        self.assertEqual([info.filename for info in infos], sorted(info.filename for info in infos))
        for info in infos:
            self.assertEqual(info.date_time, (2026, 8, 14, 0, 0, 0))
            self.assertEqual(info.create_system, 3)
            self.assertEqual(info.create_version, 20)
            self.assertEqual(info.extract_version, 20)
            self.assertEqual(info.flag_bits, 0)
            self.assertEqual(info.internal_attr, 0)
            self.assertEqual(info.external_attr, 0o100644 << 16)
            self.assertEqual(info.compress_type, zipfile.ZIP_DEFLATED)
            self.assertEqual(info.comment, b"")
            self.assertEqual(info.extra, b"")
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
        self.assertIn(prefix + "skills/chatcad/SKILL.md", names)
        self.assertIn(prefix + "skills/chatmaker/agents/openai.yaml", names)
        for specialist in ("chatduino", "chatweb", "chatcad"):
            self.assertNotIn(prefix + f"skills/{specialist}/agents/openai.yaml", names)
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
        self.assertIn(prefix + "knowledge/boards/arduino-nano-classic.yaml", names)
        self.assertIn(prefix + "knowledge/mechanical/boards/arduino-nano-classic.json", names)
        self.assertIn(prefix + "knowledge/fabrication/equipment/lasermaker-generic.json", names)
        self.assertIn(prefix + "knowledge/fabrication/materials/wood-sheet-3mm.json", names)
        self.assertIn(prefix + "packs/schemas/registry.schema.json", names)
        self.assertEqual(
            len([name for name in names if name.startswith(prefix + "packs/boards/")]),
            4,
        )
        self.assertEqual(
            len([name for name in names if name.startswith(prefix + "packs/components/")]),
            20,
        )
        self.assertEqual(
            len([name for name in names if name.startswith(prefix + "packs/recipes/")]),
            23,
        )
        self.assertEqual(
            len([name for name in names if name.startswith(prefix + "knowledge/boards/")]),
            4,
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
        self.assertFalse(any("knowledge/boards/" in name and name.endswith(".md") for name in names))


if __name__ == "__main__":
    unittest.main()
