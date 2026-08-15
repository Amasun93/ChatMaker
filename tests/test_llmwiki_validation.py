from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))
BOARDS = ("arduino-nano-classic", "arduino-uno-r3", "esp32-devkit-v1")
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


try:
    from chatmaker.installers.pack_artifact import build_pack, validate_pack_archive
except ImportError:
    build_pack = None
    validate_pack_archive = None


def load_page(path: Path):
    raw = path.read_text(encoding="utf-8")
    _, frontmatter, body = raw.split("---\n", 2)
    return yaml.safe_load(frontmatter), body


@unittest.skipIf(build_pack is None, "Task 3 deterministic builder is missing")
class LLMWikiContentValidationTests(unittest.TestCase):
    def test_core_indexes_are_exact_unique_compact_and_schema_valid(self):
        schema = yaml.safe_load(
            (ROOT / "packs" / "schemas" / "llmwiki-index.schema.yaml").read_text(
                encoding="utf-8"
            )
        )
        for board_id in BOARDS:
            with self.subTest(board_id=board_id):
                index = yaml.safe_load(
                    (
                        ROOT / "packs" / "llmwiki" / "boards" / f"{board_id}.yaml"
                    ).read_text(encoding="utf-8")
                )
                jsonschema.Draft202012Validator(schema).validate(index)
                self.assertEqual(index["board_id"], board_id)
                self.assertEqual(
                    [section["section_id"] for section in index["sections"]],
                    list(SECTIONS),
                )
                self.assertEqual(
                    {section["pack_id"] for section in index["sections"]},
                    {f"chatmaker-board-{board_id}-wiki"},
                )
                for section in index["sections"]:
                    self.assertEqual(
                        set(section),
                        {"section_id", "title", "summary", "consumers", "topics", "pack_id"},
                    )
                    self.assertEqual(
                        set(section["consumers"]),
                        {"chatmaker", "chatduino", "chatweb"},
                    )

    def test_governed_pages_have_exact_identity_source_and_bounded_beginner_body(self):
        pages = sorted((ROOT / "knowledge_sources" / "published" / "boards").glob("*/*.md"))
        self.assertEqual(len(pages), 24)
        for path in pages:
            with self.subTest(path=path):
                board_id = path.parent.name
                section_id = path.stem
                frontmatter, body = load_page(path)
                self.assertEqual(
                    frontmatter,
                    {
                        "schema_version": "1.0",
                        "kind": "llmwiki-page",
                        "stable_id": f"{board_id}-{section_id}",
                        "board_id": board_id,
                        "section_id": section_id,
                        "source_refs": [
                            "source-esp32-devkit-v1-doit-board-definition"
                            if board_id == "esp32-devkit-v1"
                            else f"source-{board_id}-documentation"
                        ],
                    },
                )
                self.assertLessEqual(len(body.encode("utf-8")), 65_536)
                self.assertIn(f"`{board_id}`", body)
                self.assertIn("canonical", body.casefold())
                self.assertGreaterEqual(len(body.split()), 25)

    def test_web_pages_preserve_connectivity_and_runtime_evidence_boundaries(self):
        for board_id in ("arduino-nano-classic", "arduino-uno-r3"):
            _, body = load_page(
                ROOT
                / "knowledge_sources"
                / "published"
                / "boards"
                / board_id
                / "web-and-protocol.md"
            )
            self.assertIn("does not have native Wi-Fi", body)
            self.assertIn("host or an extra communication route", body)

        _, esp32_body = load_page(
            ROOT
            / "knowledge_sources"
            / "published"
            / "boards"
            / "esp32-devkit-v1"
            / "web-and-protocol.md"
        )
        self.assertIn("`esp32-ap-led-sensor`", esp32_body)
        self.assertIn("unverified", esp32_body)

    def test_committed_artifacts_match_approved_sources_and_are_repeatable(self):
        for board_id in BOARDS:
            with self.subTest(board_id=board_id), tempfile.TemporaryDirectory() as directory:
                pack_id = f"chatmaker-board-{board_id}-wiki"
                artifact = ROOT / "distribution" / "packs" / f"{pack_id}-1.0.0.cmpack"
                manifest = validate_pack_archive(artifact, core_version="0.1.0")
                self.assertEqual(manifest["pack_id"], pack_id)
                self.assertEqual(len(manifest["files"]), 9)
                with zipfile.ZipFile(artifact) as archive:
                    self.assertEqual(
                        archive.read("llmwiki/index.yaml"),
                        (ROOT / "packs" / "llmwiki" / "boards" / f"{board_id}.yaml").read_bytes(),
                    )
                    for section_id in SECTIONS:
                        self.assertEqual(
                            archive.read(f"llmwiki/sections/{section_id}.md"),
                            (
                                ROOT
                                / "knowledge_sources"
                                / "published"
                                / "boards"
                                / board_id
                                / f"{section_id}.md"
                            ).read_bytes(),
                        )

                source = Path(directory) / "source" / "llmwiki"
                (source / "sections").mkdir(parents=True)
                (source / "index.yaml").write_bytes(
                    (ROOT / "packs" / "llmwiki" / "boards" / f"{board_id}.yaml").read_bytes()
                )
                for section_id in SECTIONS:
                    (source / "sections" / f"{section_id}.md").write_bytes(
                        (
                            ROOT
                            / "knowledge_sources"
                            / "published"
                            / "boards"
                            / board_id
                            / f"{section_id}.md"
                        ).read_bytes()
                    )
                rebuilt = Path(directory) / "rebuilt.cmpack"
                build_pack(
                    source.parent,
                    rebuilt,
                    pack_id=pack_id,
                    pack_version="1.0.0",
                    board_id=board_id,
                    core_minimum="0.1.0",
                    core_maximum_exclusive="0.2.0",
                )
                self.assertEqual(rebuilt.read_bytes(), artifact.read_bytes())
                self.assertEqual(
                    hashlib.sha256(rebuilt.read_bytes()).hexdigest(),
                    hashlib.sha256(artifact.read_bytes()).hexdigest(),
                )

    def test_pyproject_exposes_llmwiki_cli(self):
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('chatmaker-llmwiki = "chatmaker.llmwiki:main"', text)


if __name__ == "__main__":
    unittest.main()
