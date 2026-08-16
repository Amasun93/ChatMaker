from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.knowledge import execute_request
from chatmaker.knowledge_semantics import (
    BOARD_IDS,
    PACK_IDS,
    SECTION_IDS,
    validate_index_bytes,
    validate_pack_payload,
    validate_page_bytes,
)


BOARD_ID = "arduino-nano-classic"
PACK_ID = "chatmaker-board-arduino-nano-classic-knowledge"


def index_payload() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "kind": "knowledge-index",
        "board_id": BOARD_ID,
        "max_section_bytes": 65_536,
        "sections": [
            {
                "section_id": section_id,
                "title": section_id.replace("-", " ").title(),
                "summary": f"Bounded knowledge for {section_id}.",
                "consumers": ["chatmaker", "chatduino", "chatweb"],
                "topics": [section_id],
                "pack_id": PACK_ID,
            }
            for section_id in SECTION_IDS
        ],
    }


def page(section_id: str, body: str) -> bytes:
    return (
        "---\n"
        "schema_version: '1.0'\n"
        "kind: knowledge-page\n"
        f"stable_id: {BOARD_ID}-{section_id}\n"
        f"board_id: {BOARD_ID}\n"
        f"section_id: {section_id}\n"
        "source_refs:\n"
        "  - source-arduino-nano-classic-documentation\n"
        "---\n"
        f"{body}"
    ).encode("utf-8")


class FakeResolved:
    def __init__(self, resolver, key: tuple[str, str], data: bytes, provenance: dict):
        self.resolver = resolver
        self.key = key
        self.data = data
        self.provenance = provenance

    def read_bytes(self) -> bytes:
        self.resolver.reads.append(self.key)
        return self.data


class RecordingResolver:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], tuple[bytes, dict]] = {}
        self.resolves: list[tuple[str, str]] = []
        self.reads: list[tuple[str, str]] = []

    def put(self, pack_id: str, path: str, data: bytes) -> None:
        self.values[(pack_id, path)] = (
            data,
            {"kind": "official_pack", "pack_id": pack_id, "version": "1.0.0"},
        )

    def resolve(self, path: str, *, pack_id: str | None = None) -> FakeResolved:
        assert pack_id is not None
        key = (pack_id, path)
        self.resolves.append(key)
        if key not in self.values:
            raise FileNotFoundError(path)
        data, provenance = self.values[key]
        return FakeResolved(self, key, data, provenance)


class InstallingManager:
    def __init__(self, resolver: RecordingResolver) -> None:
        self.resolver = resolver
        self.calls: list[str] = []

    def ensure(self, pack_id: str) -> None:
        self.calls.append(pack_id)
        self.resolver.put(
            pack_id,
            "knowledge/sections/start-here.md",
            page("start-here", "Load the canonical board record.\n"),
        )


class KnowledgeReaderTests(unittest.TestCase):
    def write_index(self, root: Path) -> None:
        path = root / "packs" / "knowledge" / "boards" / f"{BOARD_ID}.yaml"
        path.parent.mkdir(parents=True)
        path.write_text(
            yaml.safe_dump(index_payload(), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    def request(self, request: object, *, root: Path, manager=None, resolver=None) -> dict:
        return execute_request(
            request,
            manager=manager,
            resolver=resolver,
            project_root=root,
        )

    def test_index_returns_metadata_without_reading_optional_bodies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_index(root)
            resolver = RecordingResolver()
            resolver.put(
                PACK_ID,
                "knowledge/sections/start-here.md",
                page("start-here", "A body must not be read by index.\n"),
            )

            result = self.request(
                {"action": "index", "board_id": BOARD_ID, "consumer": "chatduino"},
                root=root,
                resolver=resolver,
            )

        self.assertTrue(result["success"], result)
        self.assertEqual(result["sections"][0]["pack_id"], PACK_ID)
        self.assertTrue(result["sections"][0]["available"])
        self.assertFalse(result["sections"][1]["available"])
        self.assertEqual(resolver.reads, [])
        self.assertIn((PACK_ID, "knowledge/sections/start-here.md"), resolver.resolves)

    def test_section_uses_knowledge_resource_and_defaults_to_auto_install(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_index(root)
            resolver = RecordingResolver()
            manager = InstallingManager(resolver)

            result = self.request(
                {
                    "action": "section",
                    "board_id": BOARD_ID,
                    "consumer": "chatmaker",
                    "section_id": "start-here",
                },
                root=root,
                manager=manager,
                resolver=resolver,
            )

        self.assertTrue(result["success"], result)
        self.assertEqual(result["body"], "Load the canonical board record.\n")
        self.assertEqual(result["body_bytes"], 33)
        self.assertEqual(result["max_body_bytes"], 65_536)
        self.assertTrue(result["complete"])
        self.assertEqual(manager.calls, [PACK_ID])
        self.assertEqual(
            resolver.reads,
            [(PACK_ID, "knowledge/sections/start-here.md")],
        )

    def test_section_without_auto_install_never_calls_manager(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_index(root)
            resolver = RecordingResolver()
            manager = InstallingManager(resolver)

            result = self.request(
                {
                    "action": "section",
                    "board_id": BOARD_ID,
                    "consumer": "chatweb",
                    "section_id": "start-here",
                    "auto_install": False,
                },
                root=root,
                manager=manager,
                resolver=resolver,
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["error"]["code"], "offline_pack_unavailable")
        self.assertEqual(manager.calls, [])

    def test_unknown_or_malformed_identities_use_knowledge_error_codes(self):
        cases = [
            ([], "invalid_knowledge_request"),
            ({"action": "other"}, "unknown_knowledge_action"),
            (
                {"action": "index", "board_id": "arduino-nano-clasic", "consumer": "chatduino"},
                "knowledge_board_not_found",
            ),
            (
                {"action": "index", "board_id": BOARD_ID, "consumer": "other"},
                "knowledge_consumer_not_supported",
            ),
            (
                {
                    "action": "section",
                    "board_id": BOARD_ID,
                    "consumer": "chatduino",
                    "section_id": "pinout",
                },
                "knowledge_section_not_found",
            ),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_index(root)
            for request, code in cases:
                with self.subTest(code=code):
                    result = self.request(request, root=root, resolver=RecordingResolver())
                    self.assertFalse(result["success"])
                    self.assertEqual(result["error"]["code"], code)

    def test_semantic_api_rejects_old_identity_and_validates_complete_payload(self):
        index = yaml.safe_dump(index_payload(), allow_unicode=True, sort_keys=False).encode("utf-8")
        files = {"knowledge/index.yaml": index}
        files.update(
            {
                f"knowledge/sections/{section_id}.md": page(section_id, "Complete guidance.\n")
                for section_id in SECTION_IDS
            }
        )

        self.assertEqual(BOARD_IDS, ("arduino-nano-classic", "arduino-uno-r3", "esp32-devkit-v1"))
        self.assertEqual(PACK_IDS[BOARD_ID], PACK_ID)
        self.assertEqual(validate_index_bytes(index)["kind"], "knowledge-index")
        self.assertEqual(
            validate_page_bytes(
                files["knowledge/sections/start-here.md"],
                expected_board_id=BOARD_ID,
                expected_section_id="start-here",
            ).body,
            "Complete guidance.\n",
        )
        self.assertEqual(
            validate_pack_payload(
                files, expected_board_id=BOARD_ID, expected_pack_id=PACK_ID
            )["board_id"],
            BOARD_ID,
        )
        with self.assertRaises(Exception) as rejected:
            validate_index_bytes(index.replace(b"knowledge-index", b"llmwiki-index"))
        self.assertEqual(rejected.exception.reason, "knowledge_index_invalid")


if __name__ == "__main__":
    unittest.main()
