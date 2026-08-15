from __future__ import annotations

import hashlib
import io
import json
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from copy import deepcopy
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

try:
    from chatmaker.installers import pack_artifact
except (ImportError, ModuleNotFoundError):
    pack_artifact = None


class PackArtifactTests(unittest.TestCase):
    def setUp(self):
        if pack_artifact is None:
            self.fail("Task 3 pack_artifact module is missing")
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        self.source = self.root / "source"
        (self.source / "llmwiki" / "sections").mkdir(parents=True)
        (self.source / "llmwiki" / "index.yaml").write_bytes(
            b"schema_version: '1.0'\nkind: llmwiki-index\n"
        )
        (self.source / "llmwiki" / "sections" / "start-here.md").write_bytes(
            b"# Start here\n\nUse the exact board.\n"
        )

    def build(self, name: str = "pack.cmpack") -> Path:
        output = self.root / name
        pack_artifact.build_pack(
            self.source,
            output,
            pack_id="chatmaker-board-arduino-nano-classic-wiki",
            pack_version="1.0.0",
            board_id="arduino-nano-classic",
            core_minimum="0.1.0",
            core_maximum_exclusive="0.2.0",
        )
        return output

    def assert_code(self, expected: str, call, *args, **kwargs):
        with self.assertRaises(pack_artifact.PackArtifactError) as caught:
            call(*args, **kwargs)
        self.assertEqual(caught.exception.code, expected)
        return caught.exception

    def rewrite_archive(self, path: Path, transform) -> Path:
        with zipfile.ZipFile(path, "r") as source_zip:
            entries = [(info, source_zip.read(info)) for info in source_zip.infolist()]
        output = self.root / f"mutated-{len(list(self.root.glob('mutated-*')))}.cmpack"
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as target:
            target.comment = b""
            transform(target, entries)
        return output

    @staticmethod
    def canonical_info(name: str, *, mode: int = stat.S_IFREG | 0o644) -> zipfile.ZipInfo:
        info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_STORED
        info.create_system = 3
        info.external_attr = mode << 16
        info.extra = b""
        info.comment = b""
        return info

    def test_double_build_is_byte_identical_and_has_frozen_zip_metadata(self):
        first = self.build("first.cmpack")
        second = self.build("second.cmpack")
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(
            hashlib.sha256(first.read_bytes()).hexdigest(),
            hashlib.sha256(second.read_bytes()).hexdigest(),
        )
        with zipfile.ZipFile(first) as archive:
            infos = archive.infolist()
            self.assertEqual(
                [info.filename for info in infos],
                [
                    "pack-manifest.json",
                    "llmwiki/index.yaml",
                    "llmwiki/sections/start-here.md",
                ],
            )
            self.assertEqual(archive.comment, b"")
            for info in infos:
                self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
                self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertEqual(info.create_system, 3)
                self.assertEqual(info.external_attr >> 16, stat.S_IFREG | 0o644)
                self.assertEqual(info.extra, b"")
                self.assertEqual(info.comment, b"")
            manifest_bytes = archive.read("pack-manifest.json")
            self.assertTrue(manifest_bytes.endswith(b"\n"))
            manifest = json.loads(manifest_bytes)
            self.assertEqual(
                manifest_bytes,
                json.dumps(
                    manifest,
                    ensure_ascii=True,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
                + b"\n",
            )
            self.assertEqual(
                [item["path"] for item in manifest["files"]],
                ["llmwiki/index.yaml", "llmwiki/sections/start-here.md"],
            )

    def test_validates_and_extracts_exact_payload_then_revalidates_staging(self):
        archive = self.build()
        manifest = pack_artifact.validate_pack_archive(
            archive,
            core_version="0.1.0",
            pack_manifest_schema="1.0",
            llmwiki_index_schema="1.0",
        )
        self.assertEqual(manifest["pack_type"], "knowledge")
        staging = self.root / "staging"
        extracted = pack_artifact.extract_validated_pack(
            archive,
            staging,
            core_version="0.1.0",
            pack_manifest_schema="1.0",
            llmwiki_index_schema="1.0",
        )
        self.assertEqual(extracted, manifest)
        self.assertEqual(
            (staging / "llmwiki" / "sections" / "start-here.md").read_bytes(),
            b"# Start here\n\nUse the exact board.\n",
        )
        self.assertEqual(
            pack_artifact.validate_staging(staging, manifest),
            manifest,
        )
        (staging / "llmwiki" / "sections" / "start-here.md").write_bytes(b"drift")
        self.assert_code(
            "pack_content_invalid",
            pack_artifact.validate_staging,
            staging,
            manifest,
        )

    def test_extraction_uses_the_same_archive_bytes_that_were_validated(self):
        archive = self.build("original.cmpack")
        original_bytes = archive.read_bytes()
        (self.source / "llmwiki" / "sections" / "start-here.md").write_bytes(
            b"# Replaced after validation\n"
        )
        replacement = self.build("replacement.cmpack")
        real_validate = pack_artifact.validate_pack_archive

        def validate_then_swap(source, **kwargs):
            result = real_validate(source, **kwargs)
            archive.write_bytes(replacement.read_bytes())
            return result

        staging = self.root / "race-staging"
        with mock.patch.object(
            pack_artifact,
            "validate_pack_archive",
            side_effect=validate_then_swap,
        ):
            pack_artifact.extract_validated_pack(
                archive,
                staging,
                core_version="0.1.0",
            )
        self.assertNotEqual(archive.read_bytes(), original_bytes)
        self.assertEqual(
            (staging / "llmwiki" / "sections" / "start-here.md").read_bytes(),
            b"# Start here\n\nUse the exact board.\n",
        )

    def test_rejects_manifest_hash_length_extra_entry_and_duplicate_path(self):
        archive = self.build()

        def mutate_manifest(field: str, value):
            def transform(target, entries):
                for info, data in entries:
                    if info.filename == "pack-manifest.json":
                        manifest = json.loads(data)
                        manifest["files"][1][field] = value
                        data = json.dumps(
                            manifest,
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode() + b"\n"
                    target.writestr(self.canonical_info(info.filename), data)
            return transform

        wrong_length = self.rewrite_archive(archive, mutate_manifest("length", 1))
        self.assert_code(
            "pack_content_invalid",
            pack_artifact.validate_pack_archive,
            wrong_length,
            core_version="0.1.0",
        )
        wrong_hash = self.rewrite_archive(archive, mutate_manifest("sha256", "0" * 64))
        self.assert_code(
            "pack_content_invalid",
            pack_artifact.validate_pack_archive,
            wrong_hash,
            core_version="0.1.0",
        )

        def add_extra(target, entries):
            for info, data in entries:
                target.writestr(self.canonical_info(info.filename), data)
            target.writestr(self.canonical_info("llmwiki/sections/extra.md"), b"extra")

        extra = self.rewrite_archive(archive, add_extra)
        self.assert_code(
            "pack_manifest_invalid",
            pack_artifact.validate_pack_archive,
            extra,
            core_version="0.1.0",
        )

        def duplicate_manifest_path(target, entries):
            for info, data in entries:
                if info.filename == "pack-manifest.json":
                    manifest = json.loads(data)
                    duplicate = deepcopy(manifest["files"][1])
                    duplicate["length"] += 1
                    manifest["files"].append(duplicate)
                    data = json.dumps(
                        manifest,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode() + b"\n"
                target.writestr(self.canonical_info(info.filename), data)

        duplicate = self.rewrite_archive(archive, duplicate_manifest_path)
        error = self.assert_code(
            "pack_manifest_invalid",
            pack_artifact.validate_pack_archive,
            duplicate,
            core_version="0.1.0",
        )
        self.assertEqual(error.reason, "duplicate_path")

    def test_rejects_zip_slip_absolute_symlink_and_canonical_record_injection(self):
        archive = self.build()
        cases = [
            ("../escape.md", stat.S_IFREG | 0o644),
            ("/absolute.md", stat.S_IFREG | 0o644),
            ("llmwiki/sections/link.md", stat.S_IFLNK | 0o777),
            ("packs/boards/injected.yaml", stat.S_IFREG | 0o644),
        ]
        for name, mode in cases:
            with self.subTest(name=name):
                def inject(target, entries, name=name, mode=mode):
                    for info, data in entries:
                        target.writestr(self.canonical_info(info.filename), data)
                    target.writestr(self.canonical_info(name, mode=mode), b"x")

                mutated = self.rewrite_archive(archive, inject)
                self.assert_code(
                    "pack_archive_unsafe",
                    pack_artifact.validate_pack_archive,
                    mutated,
                    core_version="0.1.0",
                )

    def test_rejects_hooks_dependencies_and_incompatible_ranges(self):
        archive = self.build()

        def with_manifest_change(change):
            def transform(target, entries):
                for info, data in entries:
                    if info.filename == "pack-manifest.json":
                        manifest = json.loads(data)
                        change(manifest)
                        data = json.dumps(
                            manifest,
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode() + b"\n"
                    target.writestr(self.canonical_info(info.filename), data)
            return self.rewrite_archive(archive, transform)

        for field in ("hooks", "dependencies"):
            with self.subTest(field=field):
                mutated = with_manifest_change(lambda value, field=field: value.update({field: []}))
                self.assert_code(
                    "pack_manifest_invalid",
                    pack_artifact.validate_pack_archive,
                    mutated,
                    core_version="0.1.0",
                )

        self.assert_code(
            "pack_incompatible",
            pack_artifact.validate_pack_archive,
            archive,
            core_version="0.2.0",
        )
        self.assert_code(
            "pack_incompatible",
            pack_artifact.validate_pack_archive,
            archive,
            core_version="0.1.0",
            pack_manifest_schema="2.0",
        )
        self.assert_code(
            "pack_incompatible",
            pack_artifact.validate_pack_archive,
            archive,
            core_version="0.1.0",
            llmwiki_index_schema="2.0",
        )

    def test_rejects_file_count_single_file_and_total_size_limits(self):
        archive = self.build()
        self.assert_code(
            "pack_archive_unsafe",
            pack_artifact.validate_pack_archive,
            archive,
            core_version="0.1.0",
            max_files=2,
        )
        self.assert_code(
            "pack_archive_unsafe",
            pack_artifact.validate_pack_archive,
            archive,
            core_version="0.1.0",
            max_single_file_bytes=10,
        )
        self.assert_code(
            "pack_archive_unsafe",
            pack_artifact.validate_pack_archive,
            archive,
            core_version="0.1.0",
            max_total_bytes=40,
        )

    def test_windows_semantics_reject_aliases_traversal_and_devices(self):
        bad_paths = [
            r"\\server\share\x.md",
            r"C:relative.md",
            r"llmwiki\..\escape.md",
            "llmwiki//index.yaml",
            "llmwiki/./index.yaml",
            "llmwiki/sections/file.md:stream",
            "llmwiki/sections/CON.md",
            "llmwiki/sections/name. ",
        ]
        for value in bad_paths:
            with self.subTest(value=value):
                error = self.assert_code(
                    "pack_archive_unsafe",
                    pack_artifact.validate_archive_path,
                    value,
                )
                self.assertTrue(error.reason)

        archive = self.build()

        def add_case_alias(target, entries):
            for info, data in entries:
                target.writestr(self.canonical_info(info.filename), data)
            target.writestr(self.canonical_info("LLMWIKI/INDEX.YAML"), b"alias")

        alias = self.rewrite_archive(archive, add_case_alias)
        self.assert_code(
            "pack_archive_unsafe",
            pack_artifact.validate_pack_archive,
            alias,
            core_version="0.1.0",
        )

    def test_builder_rejects_unapproved_source_tree_and_empty_files(self):
        (self.source / "packs").mkdir()
        (self.source / "packs" / "boards.yaml").write_text("injection", encoding="utf-8")
        self.assert_code(
            "pack_content_invalid",
            self.build,
            "injection.cmpack",
        )
        (self.source / "packs" / "boards.yaml").unlink()
        (self.source / "packs").rmdir()
        (self.source / "llmwiki" / "sections" / "empty.md").write_bytes(b"")
        self.assert_code("pack_content_invalid", self.build, "empty.cmpack")

    def test_malformed_archive_returns_a_stable_error(self):
        self.assert_code(
            "pack_archive_unsafe",
            pack_artifact.validate_pack_archive,
            b"not a zip archive",
            core_version="0.1.0",
        )

    def test_staging_read_os_error_returns_a_stable_error(self):
        archive = self.build()
        manifest = pack_artifact.validate_pack_archive(archive, core_version="0.1.0")
        staging = self.root / "read-error-staging"
        pack_artifact.extract_validated_pack(archive, staging, core_version="0.1.0")
        with mock.patch.object(Path, "read_bytes", side_effect=OSError("denied")):
            self.assert_code(
                "pack_content_invalid",
                pack_artifact.validate_staging,
                staging,
                manifest,
            )

    def test_staging_link_or_reparse_is_rejected_before_any_write(self):
        archive = self.build()
        staging = self.root / "linked-staging"
        real_is_symlink = Path.is_symlink

        def simulated_link(path: Path) -> bool:
            return path == staging or real_is_symlink(path)

        with mock.patch.object(Path, "is_symlink", simulated_link):
            self.assert_code(
                "pack_archive_unsafe",
                pack_artifact.extract_validated_pack,
                archive,
                staging,
                core_version="0.1.0",
            )
        self.assertFalse(staging.exists())


class BuildPackScriptTests(unittest.TestCase):
    def test_cli_builds_a_valid_pack(self):
        if pack_artifact is None:
            self.fail("Task 3 pack_artifact module is missing")
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = root / "source"
            (source / "llmwiki" / "sections").mkdir(parents=True)
            (source / "llmwiki" / "index.yaml").write_text("schema_version: '1.0'\n", encoding="utf-8")
            (source / "llmwiki" / "sections" / "start-here.md").write_text("# Start\n", encoding="utf-8")
            output = root / "out.cmpack"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_pack.py"),
                    "--source",
                    str(source),
                    "--output",
                    str(output),
                    "--pack-id",
                    "chatmaker-board-arduino-nano-classic-wiki",
                    "--pack-version",
                    "1.0.0",
                    "--board-id",
                    "arduino-nano-classic",
                    "--core-minimum",
                    "0.1.0",
                    "--core-maximum-exclusive",
                    "0.2.0",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.is_file())
            pack_artifact.validate_pack_archive(output, core_version="0.1.0")


if __name__ == "__main__":
    unittest.main()
