from __future__ import annotations

import hashlib
import io
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from copy import deepcopy
from pathlib import Path
from unittest import mock

import yaml


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

BOARD_ID = "arduino-nano-classic"
PACK_ID = "chatmaker-board-arduino-nano-classic-wiki"
SECTIONS = (
    "start-here",
    "identify-and-safety",
    "pins-and-electrical",
    "toolchains-and-upload",
    "components-and-wiring",
    "libraries-and-examples",
    "web-and-protocol",
    "troubleshooting",
)


def create_junction(link: Path, target: Path) -> None:
    completed = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise OSError(completed.stderr or completed.stdout)


def remove_junction(path: Path) -> None:
    if os.path.lexists(path):
        os.rmdir(path)

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
            (ROOT / "packs" / "llmwiki" / "boards" / f"{BOARD_ID}.yaml").read_bytes()
        )
        for section_id in SECTIONS:
            (self.source / "llmwiki" / "sections" / f"{section_id}.md").write_bytes(
                (
                    ROOT
                    / "knowledge_sources"
                    / "published"
                    / "boards"
                    / BOARD_ID
                    / f"{section_id}.md"
                ).read_bytes()
            )

    def replace_page_body(self, section_id: str, body: str) -> None:
        path = self.source / "llmwiki" / "sections" / f"{section_id}.md"
        raw = path.read_text(encoding="utf-8")
        prefix, _, _ = raw.partition("\n---\n")
        path.write_text(prefix + "\n---\n" + body, encoding="utf-8")

    def build(self, name: str = "pack.cmpack") -> Path:
        output = self.root / name
        pack_artifact.build_pack(
            self.source,
            output,
            pack_id=PACK_ID,
            pack_version="1.0.0",
            board_id=BOARD_ID,
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
                    *[f"llmwiki/sections/{section_id}.md" for section_id in sorted(SECTIONS)],
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
                [
                    "llmwiki/index.yaml",
                    *[f"llmwiki/sections/{section_id}.md" for section_id in sorted(SECTIONS)],
                ],
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
            (
                ROOT
                / "knowledge_sources"
                / "published"
                / "boards"
                / BOARD_ID
                / "start-here.md"
            ).read_bytes(),
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
        self.replace_page_body("start-here", "# Replaced after validation\n")
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
            (
                ROOT
                / "knowledge_sources"
                / "published"
                / "boards"
                / BOARD_ID
                / "start-here.md"
            ).read_bytes(),
        )

    def test_extraction_keeps_scratch_on_destination_volume_for_atomic_move(self):
        archive = self.build()
        staging = self.root / "same-volume-staging"
        real_mkdtemp = tempfile.mkdtemp

        def reject_other_volume(*args, **kwargs):
            directory = kwargs.get("dir")
            if directory is None or Path(directory) != staging.parent:
                raise OSError("simulated cross-volume scratch")
            return real_mkdtemp(*args, **kwargs)

        with mock.patch.object(
            pack_artifact.tempfile,
            "mkdtemp",
            side_effect=reject_other_volume,
        ):
            manifest = pack_artifact.extract_validated_pack(
                archive,
                staging,
                core_version="0.1.0",
            )

        self.assertEqual(manifest["pack_id"], PACK_ID)
        self.assertTrue(
            (staging / "llmwiki" / "sections" / "start-here.md").is_file()
        )

    def test_builder_rejects_semantically_invalid_index_page_set_and_body(self):
        index_path = self.source / "llmwiki" / "index.yaml"
        index = yaml.safe_load(index_path.read_text(encoding="utf-8"))
        index["board_id"] = "arduino-uno-r3"
        index_path.write_text(
            yaml.safe_dump(index, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        error = self.assert_code("pack_content_invalid", self.build, "wrong-board.cmpack")
        self.assertEqual(error.reason, "llmwiki_index_board_mismatch")

        index_path.write_bytes(
            (ROOT / "packs" / "llmwiki" / "boards" / f"{BOARD_ID}.yaml").read_bytes()
        )
        missing = self.source / "llmwiki" / "sections" / "troubleshooting.md"
        original_missing = missing.read_bytes()
        missing.unlink()
        error = self.assert_code("pack_content_invalid", self.build, "missing-page.cmpack")
        self.assertEqual(error.reason, "llmwiki_page_set_mismatch")
        missing.write_bytes(original_missing)

        self.replace_page_body("start-here", "")
        error = self.assert_code("pack_content_invalid", self.build, "empty-body.cmpack")
        self.assertEqual(error.reason, "llmwiki_page_body_size_invalid")

    def test_builder_applies_65536_byte_limit_to_body_not_frontmatter(self):
        self.replace_page_body("start-here", "x" * 65_536)
        accepted = self.build("body-limit.cmpack")
        self.assertTrue(accepted.is_file())

        self.replace_page_body("start-here", "x" * 65_537)
        error = self.assert_code(
            "pack_content_invalid", self.build, "body-too-large.cmpack"
        )
        self.assertEqual(error.reason, "llmwiki_page_body_size_invalid")

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

    @unittest.skipUnless(os.name == "nt", "Windows junction semantics only")
    def test_extraction_swap_to_real_junction_never_writes_outside_destination(self):
        archive = self.build()
        staging = self.root / "swap-staging"
        outside = self.root / "outside-staging"
        outside.mkdir()
        calls = 0
        real_read = zipfile.ZipFile.read

        def swap_after_validation(archive_object, name, *args, **kwargs):
            nonlocal calls
            data = real_read(archive_object, name, *args, **kwargs)
            calls += 1
            if calls == 11:
                if staging.exists():
                    os.rmdir(staging)
                create_junction(staging, outside)
            return data

        try:
            with mock.patch.object(zipfile.ZipFile, "read", swap_after_validation):
                self.assert_code(
                    "pack_archive_unsafe",
                    pack_artifact.extract_validated_pack,
                    archive,
                    staging,
                    core_version="0.1.0",
                )
            self.assertEqual(list(outside.iterdir()), [])
        finally:
            remove_junction(staging)

    @unittest.skipUnless(os.name == "nt", "Windows junction semantics only")
    def test_extraction_rejects_nested_junction_before_creating_descendants(self):
        archive = self.build()
        outside = self.root / "outside-nested-staging"
        outside.mkdir()
        junction = self.root / "nested-staging-junction"
        create_junction(junction, outside)

        try:
            error = self.assert_code(
                "pack_archive_unsafe",
                pack_artifact.extract_validated_pack,
                archive,
                junction / "missing-parent" / "staging",
                core_version="0.1.0",
            )
            self.assertEqual(error.reason, "staging_link_or_reparse")
            self.assertEqual(list(outside.iterdir()), [])
        finally:
            remove_junction(junction)

    def test_regular_file_staging_returns_a_stable_error(self):
        archive = self.build()
        staging = self.root / "staging-is-a-file"
        staging.write_bytes(b"occupied")
        error = self.assert_code(
            "pack_content_invalid",
            pack_artifact.extract_validated_pack,
            archive,
            staging,
            core_version="0.1.0",
        )
        self.assertEqual(error.reason, "staging_not_directory")
        self.assertEqual(staging.read_bytes(), b"occupied")


class BuildPackScriptTests(unittest.TestCase):
    def prepare_documented_source(self, root: Path, board_id: str = "arduino-nano-classic") -> Path:
        source = root / "prepared-source-root" / "llmwiki"
        (source / "sections").mkdir(parents=True)
        (source / "index.yaml").write_bytes(
            (ROOT / "packs" / "llmwiki" / "boards" / f"{board_id}.yaml").read_bytes()
        )
        for page in sorted(
            (ROOT / "knowledge_sources" / "published" / "boards" / board_id).glob("*.md")
        ):
            (source / "sections" / page.name).write_bytes(page.read_bytes())
        return source.parent

    def test_cli_builds_a_valid_pack(self):
        if pack_artifact is None:
            self.fail("Task 3 pack_artifact module is missing")
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self.prepare_documented_source(root)
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

    def test_pack_format_docs_build_example_matches_cli_and_source_contract(self):
        if pack_artifact is None:
            self.fail("Task 3 pack_artifact module is missing")
        document = (ROOT / "docs" / "contributing" / "pack-format.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("pack-manifest.json", document)
        self.assertIn("llmwiki/index.yaml", document)
        self.assertIn("llmwiki/sections/<section-id>.md", document)
        self.assertIn(
            "Do not pass `knowledge_sources/published/boards/<board-id>` directly to `--source`",
            document,
        )
        match = re.search(
            r"python scripts/build_pack\.py --source <prepared-source-root> --output <output-pack-path> --pack-id (?P<pack_id>\S+) --pack-version (?P<pack_version>\S+) --board-id (?P<board_id>\S+) --core-minimum (?P<core_minimum>\S+) --core-maximum-exclusive (?P<core_maximum_exclusive>\S+)",
            document,
        )
        self.assertIsNotNone(match)
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self.prepare_documented_source(root, board_id=match["board_id"])
            output = root / "documented-example.cmpack"
            command = [
                sys.executable,
                str(ROOT / "scripts" / "build_pack.py"),
                "--source",
                str(source),
                "--output",
                str(output),
                "--pack-id",
                match["pack_id"],
                "--pack-version",
                match["pack_version"],
                "--board-id",
                match["board_id"],
                "--core-minimum",
                match["core_minimum"],
                "--core-maximum-exclusive",
                match["core_maximum_exclusive"],
            ]
            result = subprocess.run(
                command,
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = pack_artifact.validate_pack_archive(output, core_version="0.1.0")
            self.assertEqual(manifest["pack_id"], match["pack_id"])
            self.assertEqual(manifest["board_id"], match["board_id"])


if __name__ == "__main__":
    unittest.main()
