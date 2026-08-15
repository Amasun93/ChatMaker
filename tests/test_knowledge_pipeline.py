from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

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
    def make_workspace(self, root: Path) -> Path:
        workspace = root / "knowledge_sources"
        shutil.copytree(ROOT / "knowledge_sources", workspace)
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
        source_refs: list[str] | None = None,
        body: str = "Use the canonical board record before following this guide.\n",
    ) -> None:
        source_refs = source_refs or ["source-arduino-nano-classic-documentation"]
        frontmatter = {
            "schema_version": "1.0",
            "kind": "llmwiki-page",
            "stable_id": stable_id,
            "board_id": "arduino-nano-classic",
            "section_id": "start-here",
            "source_refs": source_refs,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "---\n"
            + yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)
            + "---\n"
            + body,
            encoding="utf-8",
        )

    def validate(self, root: Path) -> dict:
        return load_validator().validate_knowledge_publication(root)

    def test_checked_in_manifests_cover_exact_boards_without_promoting_unverified_gates(self):
        result = self.validate(ROOT)

        self.assertTrue(result["success"], result["errors"])
        self.assertEqual(result["counts"], {"manifests": 3, "pages": 0})
        expected_boards = {
            "arduino-nano-classic",
            "arduino-uno-r3",
            "esp32-devkit-v1",
        }
        actual_boards = set()
        for path in (ROOT / "knowledge_sources" / "manifests").glob("*.yaml"):
            manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
            actual_boards.add(manifest["board_id"])
            self.assertEqual(manifest["cleaning_verified"]["status"], "unverified")
            self.assertEqual(manifest["publication_approved"]["status"], "unverified")
        self.assertEqual(actual_boards, expected_boards)

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
        self.assertEqual(result["counts"], {"manifests": 3, "pages": 1})

    def test_rejects_escaping_page_declaration_and_malformed_frontmatter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = self.make_workspace(root)
            self.declare_page(workspace, path="published/boards/arduino-nano-classic/../../escape.md")
            malformed = workspace / "published" / "boards" / "arduino-nano-classic" / "broken.md"
            malformed.parent.mkdir(parents=True, exist_ok=True)
            malformed.write_text("---\nnot: [valid\n---\nbody\n", encoding="utf-8")

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

    def test_check_only_cli_emits_structured_json_and_nonzero_on_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = self.make_workspace(Path(directory))
            (workspace / "manifests" / "arduino-uno-r3.yaml").unlink()
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "validate_knowledge_publication.py"),
                    "--root",
                    directory,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertNotEqual(completed.returncode, 0)
        result = json.loads(completed.stdout)
        self.assertFalse(result["success"])
        self.assertTrue(any("missing source manifest" in error for error in result["errors"]), result)


if __name__ == "__main__":
    unittest.main()
