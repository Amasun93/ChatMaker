from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_validator():
    import importlib.util

    path = ROOT / "scripts" / "validate_knowledge_publication.py"
    spec = importlib.util.spec_from_file_location("validate_knowledge_publication", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_yaml(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")


def approved_gate() -> dict[str, str]:
    return {
        "status": "verified",
        "date": "2026-08-16",
        "evidence": "A designated maintainer approved this exact page declaration.",
    }


class KnowledgePublicationPipelineTests(unittest.TestCase):
    STARCORE_MODULE_IDS = {
        "IDMD-0001",
        "IDMD-0002",
        "IDMD-0021",
        "IDMS-0001",
        "IDMS-0003",
        "IDMS-0008",
        "IDMS-0009",
        "IDMM-0007",
    }

    def make_workspace(self, root: Path) -> Path:
        workspace = root / "knowledge_sources"
        shutil.copytree(ROOT / "knowledge_sources", workspace)
        shutil.rmtree(workspace / "published", ignore_errors=True)
        for manifest_path in (workspace / "manifests").glob("*.yaml"):
            manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            manifest["publication_approved"] = {
                "status": "unverified",
                "date": None,
                "evidence": None,
            }
            manifest["page_declarations"] = []
            write_yaml(manifest_path, manifest)
        return workspace

    def manifest(self, workspace: Path, board_id: str = "arduino-nano-classic") -> tuple[Path, dict]:
        path = workspace / "manifests" / f"{board_id}.yaml"
        return path, yaml.safe_load(path.read_text(encoding="utf-8"))

    def declare_page(self, workspace: Path, *, path: str = "published/boards/arduino-nano-classic/start-here.md", stable_id: str = "arduino-nano-classic-start-here") -> Path:
        manifest_path, manifest = self.manifest(workspace)
        manifest["publication_approved"] = approved_gate()
        manifest["page_declarations"] = [{"stable_id": stable_id, "path": path}]
        write_yaml(manifest_path, manifest)
        return workspace / path

    def write_page(
        self,
        path: Path,
        *,
        stable_id: str = "arduino-nano-classic-start-here",
        source_refs: Any = None,
        board_id: Any = "arduino-nano-classic",
        section_id: Any = "start-here",
        body: str = "Use the canonical board record before following this guide.\n",
        extra_frontmatter: dict[str, Any] | None = None,
    ) -> None:
        if source_refs is None:
            source_refs = ["source-arduino-nano-classic-documentation"]
        frontmatter = {
            "schema_version": "1.0",
            "kind": "knowledge-page",
            "stable_id": stable_id,
            "board_id": board_id,
            "section_id": section_id,
            "source_refs": source_refs,
        }
        frontmatter.update(extra_frontmatter or {})
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "---\n"
            + yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)
            + "---\n"
            + body,
            encoding="utf-8",
            newline="\n",
        )

    def validate(self, root: Path) -> dict:
        return load_validator().validate_knowledge_publication(root)

    def run_cli(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "validate_knowledge_publication.py"),
                "--root",
                str(root),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_checked_in_manifests_cover_exact_governed_pages_without_promoting_source_gates(self):
        result = self.validate(ROOT)

        self.assertTrue(result["success"], result["errors"])
        self.assertEqual(result["counts"], {"manifests": 6, "pages": 48})
        expected_boards = {
            "arduino-nano-classic",
            "arduino-uno-r3",
            "esp32-devkit-v1",
            "idmc-0001-starcore-v4-2-2",
            "mpython-classic-v2x",
            "mpython-v3",
        }
        actual_boards = set()
        for path in (ROOT / "knowledge_sources" / "manifests").glob("*.yaml"):
            manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
            actual_boards.add(manifest["board_id"])
            expected_cleaning = (
                "verified"
                if manifest["board_id"] in {
                    "idmc-0001-starcore-v4-2-2",
                    "mpython-classic-v2x",
                    "mpython-v3",
                }
                else "unverified"
            )
            self.assertEqual(manifest["cleaning_verified"]["status"], expected_cleaning)
            self.assertEqual(manifest["publication_approved"]["status"], "verified")
            self.assertEqual(len(manifest["page_declarations"]), 8)
            if manifest["board_id"] in {"arduino-nano-classic", "arduino-uno-r3"}:
                self.assertEqual(manifest["source_reviewed"]["status"], "unverified")
        self.assertEqual(actual_boards, expected_boards)

    def test_starcore_manifest_governs_exact_approved_module_rewrites(self):
        manifest = yaml.safe_load(
            (
                ROOT
                / "knowledge_sources"
                / "manifests"
                / "idmc-0001-starcore-v4-2-2.yaml"
            ).read_text(encoding="utf-8")
        )

        migrations = manifest["module_migrations"]
        self.assertEqual({item["hardware_id"] for item in migrations}, self.STARCORE_MODULE_IDS)
        self.assertEqual(len(migrations), len(self.STARCORE_MODULE_IDS))
        evidence_ids = {item["source_id"] for item in manifest["source_evidence"]}
        for item in migrations:
            self.assertTrue(item["approved_rewritten_uses"])
            self.assertTrue(set(item["source_ids"]).issubset(evidence_ids))
        for evidence in manifest["source_evidence"]:
            self.assertRegex(evidence["sha256"], r"^[0-9a-f]{64}$")
        self.assertIn("normalized facts", manifest["publication_boundary"]["public"])
        self.assertIn("manufacturing source files", manifest["publication_boundary"]["private"])

    def test_publication_validator_rejects_private_local_source_references(self):
        for leaked_reference in (r"C:\private\module.txt", "private/module.step"):
            with self.subTest(leaked_reference=leaked_reference), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                workspace = self.make_workspace(root)
                manifest_path, manifest = self.manifest(
                    workspace, "idmc-0001-starcore-v4-2-2"
                )
                manifest["source_evidence"][0]["description"] = leaked_reference
                write_yaml(manifest_path, manifest)

                result = self.validate(root)

                self.assertFalse(result["success"])
                self.assertTrue(
                    any("private source reference" in error for error in result["errors"]),
                    result,
                )

    def test_page_path_is_exact_board_filename_depth_and_section_matches_stem(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = self.make_workspace(root)
            nested = self.declare_page(
                workspace,
                path="published/boards/arduino-nano-classic/nested/start-here.md",
            )
            self.write_page(nested)

            nested_result = self.validate(root)

        self.assertFalse(nested_result["success"])
        self.assertTrue(any("unsafe page path" in error for error in nested_result["errors"]))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = self.make_workspace(root)
            page_path = self.declare_page(workspace)
            self.write_page(page_path, section_id="troubleshooting")

            mismatch_result = self.validate(root)

        self.assertFalse(mismatch_result["success"])
        self.assertTrue(any("filename stem" in error for error in mismatch_result["errors"]))

    def test_page_requires_a_separate_publication_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = self.make_workspace(Path(directory))
            manifest_path, manifest = self.manifest(workspace)
            manifest["page_declarations"] = [{
                "stable_id": "arduino-nano-classic-start-here",
                "path": "published/boards/arduino-nano-classic/start-here.md",
            }]
            write_yaml(manifest_path, manifest)
            self.write_page(workspace / manifest["page_declarations"][0]["path"])

            result = self.validate(Path(directory))

        self.assertFalse(result["success"])
        self.assertTrue(any("publication_approved" in error for error in result["errors"]), result)

    def test_approved_page_must_use_safe_path_valid_frontmatter_and_known_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = self.make_workspace(Path(directory))
            page_path = self.declare_page(workspace)
            self.write_page(page_path)

            result = self.validate(Path(directory))

        self.assertTrue(result["success"], result["errors"])
        self.assertEqual(result["counts"], {"manifests": 6, "pages": 1})

    def test_page_uses_exact_six_fields_and_a_nonempty_body(self):
        for body, extra_frontmatter in (
            ("Valid body.\n", {"title": "Duplicate display title"}),
            (" \n\t", None),
        ):
            with self.subTest(body=body, extra=extra_frontmatter), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                workspace = self.make_workspace(root)
                page_path = self.declare_page(workspace)
                self.write_page(
                    page_path,
                    body=body,
                    extra_frontmatter=extra_frontmatter,
                )

                result = self.validate(root)

            self.assertFalse(result["success"], result)
            self.assertTrue(
                any("Knowledge semantic" in error for error in result["errors"]),
                result,
            )

    def test_rejects_escaping_page_declaration_and_malformed_frontmatter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = self.make_workspace(root)
            self.declare_page(workspace, path="published/boards/arduino-nano-classic/../../escape.md")
            malformed = workspace / "published" / "boards" / "arduino-nano-classic" / "broken.md"
            malformed.parent.mkdir(parents=True, exist_ok=True)
            malformed.write_text(
                "---\nnot: [valid\n---\nbody\n", encoding="utf-8", newline="\n"
            )

            result = self.validate(root)

        self.assertFalse(result["success"])
        self.assertTrue(any("unsafe page path" in error for error in result["errors"]), result)
        self.assertTrue(any("frontmatter" in error for error in result["errors"]), result)

    def test_rejects_unsupported_schema_duplicate_stable_id_missing_source_and_oversized_body(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = self.make_workspace(root)
            page_one = self.declare_page(workspace)
            self.write_page(page_one, source_refs=["missing-source"])
            manifest_path, manifest = self.manifest(workspace, "arduino-uno-r3")
            manifest["schema_version"] = "9.9"
            manifest["publication_approved"] = approved_gate()
            manifest["page_declarations"] = [{
                "stable_id": "arduino-nano-classic-start-here",
                "path": "published/boards/arduino-uno-r3/too-large.md",
            }]
            write_yaml(manifest_path, manifest)
            page_two = workspace / manifest["page_declarations"][0]["path"]
            self.write_page(
                page_two,
                stable_id="arduino-nano-classic-start-here",
                body="x" * 65_537,
            )

            result = self.validate(root)

        self.assertFalse(result["success"])
        self.assertTrue(any("unsupported schema_version" in error for error in result["errors"]), result)
        self.assertTrue(any("duplicate stable_id" in error for error in result["errors"]), result)
        self.assertTrue(any("missing source reference" in error for error in result["errors"]), result)
        self.assertTrue(any("65,536" in error for error in result["errors"]), result)

    def test_verified_gates_require_their_own_date_and_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = self.make_workspace(Path(directory))
            manifest_path, manifest = self.manifest(workspace)
            manifest["cleaning_verified"] = {
                "status": "verified",
                "date": None,
                "evidence": None,
            }
            write_yaml(manifest_path, manifest)

            result = self.validate(Path(directory))

        self.assertFalse(result["success"])
        self.assertTrue(any("cleaning_verified" in error for error in result["errors"]), result)

    def test_malformed_frontmatter_types_return_structured_cli_errors(self):
        for field, value in (
            ("source_refs", {"not": "a list of strings"}),
            ("source_refs", [{"not": "a scalar source ID"}]),
            ("section_id", {"not": "a section ID"}),
        ):
            with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                workspace = self.make_workspace(root)
                page_path = self.declare_page(workspace)
                arguments: dict[str, Any] = {field: value}
                self.write_page(page_path, **arguments)

                completed = self.run_cli(root)

            self.assertNotEqual(completed.returncode, 0, completed.stdout)
            result = json.loads(completed.stdout)
            self.assertFalse(result["success"])
            self.assertTrue(
                any("malformed frontmatter" in error for error in result["errors"]),
                result,
            )

    def test_manifest_board_scope_must_match_its_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = self.make_workspace(root)
            manifest_path, manifest = self.manifest(workspace)
            manifest["board_id"] = "arduino-uno-r3"
            write_yaml(manifest_path, manifest)

            result = self.validate(root)

        self.assertFalse(result["success"])
        self.assertTrue(any("does not match filename" in error for error in result["errors"]), result)

    def test_page_sources_must_belong_to_its_declaring_approved_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = self.make_workspace(root)
            page_path = self.declare_page(workspace)
            self.write_page(page_path, source_refs=["source-arduino-uno-r3-documentation"])

            result = self.validate(root)

        self.assertFalse(result["success"])
        self.assertTrue(any("declaring approved manifest" in error for error in result["errors"]), result)

    def test_rejects_manifest_and_page_reparse_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = self.make_workspace(root)
            manifest_path, _ = self.manifest(workspace)
            page_path = self.declare_page(workspace)
            self.write_page(page_path)
            validator = load_validator()
            reparse_paths = {manifest_path, page_path}
            with patch.object(
                validator,
                "_is_link_or_reparse",
                side_effect=lambda candidate: Path(candidate) in reparse_paths,
            ):
                result = validator.validate_knowledge_publication(root)

        self.assertFalse(result["success"])
        self.assertTrue(any("unsafe manifest filesystem path" in error for error in result["errors"]), result)
        self.assertTrue(any("unsafe page filesystem path" in error for error in result["errors"]), result)

    def test_rejects_schema_reparse_traversal_before_loading_external_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = self.make_workspace(root)
            schema_path = workspace / "schemas" / "source-manifest.schema.yaml"
            validator = load_validator()
            with patch.object(
                validator,
                "_is_link_or_reparse",
                side_effect=lambda candidate: Path(candidate) == schema_path,
            ):
                result = validator.validate_knowledge_publication(root)

        self.assertFalse(result["success"])
        self.assertEqual(result["counts"], {"manifests": 0, "pages": 0})
        self.assertTrue(any("unsafe schema filesystem path" in error for error in result["errors"]), result)

    def test_check_only_cli_emits_structured_json_and_nonzero_on_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = self.make_workspace(Path(directory))
            (workspace / "manifests" / "arduino-uno-r3.yaml").unlink()
            completed = self.run_cli(Path(directory))

        self.assertNotEqual(completed.returncode, 0)
        result = json.loads(completed.stdout)
        self.assertFalse(result["success"])
        self.assertTrue(any("missing source manifest" in error for error in result["errors"]), result)


if __name__ == "__main__":
    unittest.main()
