from __future__ import annotations

import base64
import hashlib
import json
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))
PACK_ID = "chatmaker-board-arduino-nano-classic-wiki"
BOARD_ID = "arduino-nano-classic"
REGISTRY_URL = (
    "https://raw.githubusercontent.com/Amasun93/ChatMaker/main/"
    "distribution/registry/registry.json"
)
SIGNATURE_URL = REGISTRY_URL.replace("registry.json", "registry.sig.json")
NOW = datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc)


try:
    from chatmaker.installers.pack_artifact import build_pack
    from chatmaker.installers.pack_manager import (
        FetchResponse,
        PackManager,
        PackManagerError,
    )
    from chatmaker.llmwiki import execute_request
    from chatmaker.resources import ResourceResolver
except ImportError:
    build_pack = None
    FetchResponse = None
    PackManager = None
    PackManagerError = None
    execute_request = None
    ResourceResolver = None


def page(board_id: str, section_id: str, body: str) -> str:
    source_ref = f"source-{board_id}-documentation"
    return (
        "---\n"
        "schema_version: '1.0'\n"
        "kind: llmwiki-page\n"
        f"stable_id: {board_id}-{section_id}\n"
        f"board_id: {board_id}\n"
        f"section_id: {section_id}\n"
        "source_refs:\n"
        f"  - {source_ref}\n"
        "---\n"
        f"{body}"
    )


class FakeResolved:
    def __init__(self, resolver, key, text, provenance):
        self.resolver = resolver
        self.key = key
        self.text = text
        self.provenance = provenance

    def read_bytes(self):
        self.resolver.reads.append(self.key)
        return self.text.encode("utf-8")


class RecordingResolver:
    def __init__(self):
        self.values = {}
        self.resolves = []
        self.reads = []

    def put(self, pack_id, path, text, *, version="1.0.0"):
        self.values[(pack_id, path)] = (
            text,
            {"kind": "official_pack", "pack_id": pack_id, "version": version},
        )

    def resolve(self, path, *, pack_id=None):
        key = (pack_id, str(path))
        self.resolves.append(key)
        if key not in self.values:
            raise FileNotFoundError(str(path))
        text, provenance = self.values[key]
        return FakeResolved(self, key, text, provenance)


class InstallingManager:
    def __init__(self, resolver):
        self.resolver = resolver
        self.calls = []

    def ensure(self, pack_id):
        self.calls.append(pack_id)
        self.resolver.put(
            pack_id,
            "llmwiki/sections/start-here.md",
            page(BOARD_ID, "start-here", "Load canonical board `arduino-nano-classic`.\n"),
        )
        return {"success": True, "pack_id": pack_id, "version": "1.0.0"}


class MemoryTransport:
    def __init__(self):
        self.responses = {}
        self.calls = []
        self.lock = threading.Lock()

    def set(self, url, data, *, final_url=None):
        self.responses[url] = (data, final_url or url)

    def fetch(self, url):
        with self.lock:
            self.calls.append(url)
            response = self.responses[url]
        if isinstance(response, BaseException):
            raise response
        data, final_url = response
        return FetchResponse(data=data, final_url=final_url)


class SignedRegistryFixture:
    def __init__(self, root: Path):
        self.root = root
        self.user_root = root / "user"
        self.transport = MemoryTransport()
        self.private_key = Ed25519PrivateKey.generate()
        public = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.trust_store = {
            "schema_version": "1.0",
            "registry_url": REGISTRY_URL,
            "signature_url": SIGNATURE_URL,
            "keys": [
                {
                    "key_id": "test-official",
                    "algorithm": "ed25519",
                    "public_key_base64": base64.b64encode(public).decode("ascii"),
                    "fingerprint_sha256": hashlib.sha256(public).hexdigest(),
                    "status": "active",
                    "not_before": "2026-08-01T00:00:00Z",
                    "not_after": None,
                }
            ],
        }

    def archive(self, version: str, body: str) -> bytes:
        source = self.root / "sources" / version
        (source / "llmwiki" / "sections").mkdir(parents=True, exist_ok=True)
        (source / "llmwiki" / "index.yaml").write_bytes(
            (ROOT / "packs" / "llmwiki" / "boards" / f"{BOARD_ID}.yaml").read_bytes()
        )
        (source / "llmwiki" / "sections" / "start-here.md").write_text(
            page(BOARD_ID, "start-here", body), encoding="utf-8", newline="\n"
        )
        output = self.root / "build" / f"{version}.cmpack"
        build_pack(
            source,
            output,
            pack_id=PACK_ID,
            pack_version=version,
            board_id=BOARD_ID,
            core_minimum="0.1.0",
            core_maximum_exclusive="0.2.0",
        )
        return output.read_bytes()

    def publish(self, version: str, sequence: int, body: str, *, corrupt=False):
        archive = self.archive(version, body)
        pack_url = (
            "https://raw.githubusercontent.com/Amasun93/ChatMaker/"
            f"{sequence:040x}/distribution/packs/{PACK_ID}-{version}.cmpack"
        )
        registry = {
            "schema_version": "1.0",
            "sequence": sequence,
            "generated_at": "2026-08-16T00:00:00Z",
            "expires_at": "2026-08-23T00:00:00Z",
            "packs": [
                {
                    "pack_id": PACK_ID,
                    "pack_type": "knowledge",
                    "version": version,
                    "board_id": BOARD_ID,
                    "url": pack_url,
                    "length": len(archive),
                    "sha256": hashlib.sha256(archive).hexdigest(),
                    "compatibility": {
                        "core": {
                            "minimum": "0.1.0",
                            "maximum_exclusive": "0.2.0",
                        },
                        "pack_manifest_schema": ["1.0"],
                        "llmwiki_index_schema": ["1.0"],
                    },
                }
            ],
        }
        raw = json.dumps(registry, separators=(",", ":")).encode("utf-8") + b"\n"
        signature = self.private_key.sign(raw)
        if corrupt:
            signature = bytes([signature[0] ^ 1]) + signature[1:]
        detached = json.dumps(
            {
                "key_id": "test-official",
                "algorithm": "ed25519",
                "signature": base64.b64encode(signature).decode("ascii"),
            },
            separators=(",", ":"),
        ).encode("utf-8")
        self.transport.set(REGISTRY_URL, raw)
        self.transport.set(SIGNATURE_URL, detached)
        self.transport.set(pack_url, archive)
        return pack_url

    def manager(self):
        return PackManager(
            user_root=self.user_root,
            transport=self.transport,
            trust_store=self.trust_store,
            registry_url=REGISTRY_URL,
            signature_url=SIGNATURE_URL,
            core_version="0.1.0",
            now=NOW,
        )


class LLMWikiReaderTests(unittest.TestCase):
    def setUp(self):
        if execute_request is None:
            self.fail("Task 5 LLMWiki reader is missing")

    def request(self, value, *, manager=None, resolver=None):
        return execute_request(value, manager=manager, resolver=resolver, project_root=ROOT)

    def test_index_returns_exact_compact_sections_without_reading_any_body(self):
        resolver = RecordingResolver()
        resolver.put(
            PACK_ID,
            "llmwiki/sections/start-here.md",
            page(BOARD_ID, "start-here", "Hidden body.\n"),
        )

        result = self.request(
            {"action": "index", "board_id": BOARD_ID, "consumer": "chatduino"},
            resolver=resolver,
        )

        self.assertTrue(result["success"], result)
        self.assertEqual(
            set(result),
            {"success", "api_version", "action", "board_id", "consumer", "sections"},
        )
        self.assertEqual(len(result["sections"]), 8)
        self.assertEqual(result["sections"][0]["section_id"], "start-here")
        self.assertTrue(result["sections"][0]["available"])
        self.assertFalse(result["sections"][1]["available"])
        self.assertEqual(resolver.reads, [])

    def test_section_defaults_auto_install_and_only_reads_selected_body_once(self):
        resolver = RecordingResolver()
        manager = InstallingManager(resolver)
        request = {
            "action": "section",
            "board_id": BOARD_ID,
            "consumer": "chatmaker",
            "section_id": "start-here",
        }

        first = self.request(request, manager=manager, resolver=resolver)
        second = self.request(request, manager=manager, resolver=resolver)

        self.assertTrue(first["success"], first)
        self.assertEqual(first["body"], "Load canonical board `arduino-nano-classic`.\n")
        self.assertEqual(first["body_bytes"], len(first["body"].encode("utf-8")))
        self.assertEqual(first["max_body_bytes"], 65_536)
        self.assertTrue(first["complete"])
        self.assertNotIn("cursor", first)
        self.assertEqual(manager.calls, [PACK_ID])
        selected = (PACK_ID, "llmwiki/sections/start-here.md")
        self.assertEqual(resolver.reads, [selected, selected])
        self.assertTrue(second["success"], second)

    def test_auto_install_false_never_calls_manager_and_returns_frozen_missing_error(self):
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
            manager=manager,
            resolver=resolver,
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["error"]["code"], "offline_pack_unavailable")
        self.assertFalse(result["error"]["retryable"])
        self.assertEqual(manager.calls, [])

    def test_identity_and_request_errors_are_structured_without_fuzzy_fallback(self):
        cases = [
            ([], "invalid_llmwiki_request"),
            ({"action": 7}, "invalid_llmwiki_request"),
            ({"action": "other"}, "unknown_llmwiki_action"),
            (
                {"action": "index", "board_id": "arduino-nano-clasic", "consumer": "chatduino"},
                "llmwiki_board_not_found",
            ),
            (
                {"action": "index", "board_id": BOARD_ID, "consumer": "other"},
                "llmwiki_consumer_not_supported",
            ),
            (
                {
                    "action": "section",
                    "board_id": BOARD_ID,
                    "consumer": "chatduino",
                    "section_id": "pinout",
                },
                "llmwiki_section_not_found",
            ),
            (
                {
                    "action": "section",
                    "board_id": BOARD_ID,
                    "consumer": "chatduino",
                    "section_id": "start-here",
                    "auto_install": "yes",
                },
                "invalid_llmwiki_request",
            ),
        ]
        for request, code in cases:
            with self.subTest(code=code):
                result = self.request(request, resolver=RecordingResolver())
                self.assertFalse(result["success"])
                self.assertEqual(result["api_version"], "1")
                self.assertEqual(result["error"]["code"], code)
                self.assertNotIn("cursor", result)
                self.assertNotIn("suggestion", result)

    def test_malformed_page_identity_fails_closed(self):
        resolver = RecordingResolver()
        resolver.put(
            PACK_ID,
            "llmwiki/sections/start-here.md",
            page("arduino-uno-r3", "start-here", "Wrong board.\n"),
        )

        result = self.request(
            {
                "action": "section",
                "board_id": BOARD_ID,
                "consumer": "chatduino",
                "section_id": "start-here",
            },
            resolver=resolver,
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["error"]["code"], "pack_content_invalid")

    def test_signed_registry_downloads_once_then_cached_offline_read_survives_bad_updates(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = SignedRegistryFixture(Path(directory))
            pack_url = fixture.publish(
                "1.0.0", 1, "Load canonical board `arduino-nano-classic`.\n"
            )
            manager = fixture.manager()
            resolver = ResourceResolver(
                user_root=fixture.user_root,
                builtin_root=Path(directory) / "builtin",
                manager=manager,
                environ={},
            )
            request = {
                "action": "section",
                "board_id": BOARD_ID,
                "consumer": "chatduino",
                "section_id": "start-here",
            }

            first = self.request(request, manager=manager, resolver=resolver)
            calls_after_first = list(fixture.transport.calls)
            second = self.request(request, manager=manager, resolver=resolver)
            fixture.transport.responses = {
                url: AssertionError(f"offline read attempted {url}")
                for url in fixture.transport.responses
            }
            offline = self.request(request, manager=manager, resolver=resolver)

            self.assertTrue(first["success"], first)
            self.assertTrue(second["success"], second)
            self.assertTrue(offline["success"], offline)
            self.assertEqual(fixture.transport.calls, calls_after_first)
            self.assertEqual(calls_after_first.count(pack_url), 1)

            fixture.publish("1.1.0", 2, "Replacement.\n", corrupt=True)
            with self.assertRaises(PackManagerError) as bad_signature:
                manager.update(PACK_ID)
            self.assertEqual(bad_signature.exception.code, "registry_signature_invalid")
            after_bad_signature = self.request(request, manager=manager, resolver=resolver)

            fixture.publish("1.1.0", 1, "Replay replacement.\n")
            with self.assertRaises(PackManagerError) as replay:
                manager.update(PACK_ID)
            self.assertEqual(replay.exception.code, "registry_replay_detected")
            after_replay = self.request(request, manager=manager, resolver=resolver)

            expected = "Load canonical board `arduino-nano-classic`.\n"
            self.assertEqual(after_bad_signature["body"], expected)
            self.assertEqual(after_replay["body"], expected)


if __name__ == "__main__":
    unittest.main()
