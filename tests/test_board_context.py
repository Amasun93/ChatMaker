from __future__ import annotations

import base64
import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.catalog import get_catalog_record, open_board  # noqa: E402
from chatmaker.installers.pack_artifact import build_pack  # noqa: E402
from chatmaker.installers.pack_manager import FetchResponse, PackManager  # noqa: E402
from chatmaker.llmwiki import execute_request as llmwiki_request  # noqa: E402
from chatmaker.packs import canonical_verification_snapshot  # noqa: E402
from chatmaker.resources import ResourceResolver  # noqa: E402


PACK_ID = "chatmaker-board-arduino-nano-classic-wiki"
BOARD_ID = "arduino-nano-classic"
SECTION_IDS = (
    "start-here",
    "identify-and-safety",
    "pins-and-electrical",
    "toolchains-and-upload",
    "components-and-wiring",
    "libraries-and-examples",
    "web-and-protocol",
    "troubleshooting",
)
REGISTRY_URL = (
    "https://raw.githubusercontent.com/Amasun93/ChatMaker/main/"
    "distribution/registry/registry.json"
)
SIGNATURE_URL = REGISTRY_URL.replace("registry.json", "registry.sig.json")
NOW = datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)


def page(body: str) -> str:
    return (
        "---\n"
        "schema_version: '1.0'\n"
        "kind: llmwiki-page\n"
        f"stable_id: {BOARD_ID}-start-here\n"
        f"board_id: {BOARD_ID}\n"
        "section_id: start-here\n"
        "source_refs:\n"
        "  - source-arduino-nano-classic-documentation\n"
        "---\n"
        f"{body}"
    )


class MemoryTransport:
    def __init__(self):
        self.responses = {}

    def set(self, url, data, *, final_url=None):
        self.responses[url] = (data, final_url or url)

    def fetch(self, url):
        data, final_url = self.responses[url]
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

    def publish(self, version: str, body: str) -> None:
        source = self.root / "source"
        (source / "llmwiki" / "sections").mkdir(parents=True, exist_ok=True)
        (source / "llmwiki" / "index.yaml").write_bytes(
            (ROOT / "packs" / "llmwiki" / "boards" / f"{BOARD_ID}.yaml").read_bytes()
        )
        for section_id in SECTION_IDS:
            target = source / "llmwiki" / "sections" / f"{section_id}.md"
            if section_id == "start-here":
                target.write_text(page(body), encoding="utf-8", newline="\n")
            else:
                target.write_bytes(
                    (
                        ROOT
                        / "knowledge_sources"
                        / "published"
                        / "boards"
                        / BOARD_ID
                        / f"{section_id}.md"
                    ).read_bytes()
                )
        archive = self.root / f"{PACK_ID}-{version}.cmpack"
        build_pack(
            source,
            archive,
            pack_id=PACK_ID,
            pack_version=version,
            board_id=BOARD_ID,
            core_minimum="0.1.0",
            core_maximum_exclusive="0.2.0",
        )
        archive_bytes = archive.read_bytes()
        pack_url = (
            "https://raw.githubusercontent.com/Amasun93/ChatMaker/"
            + ("1" * 40)
            + f"/distribution/packs/{PACK_ID}-{version}.cmpack"
        )
        registry = {
            "schema_version": "1.0",
            "sequence": 1,
            "generated_at": "2026-08-15T00:00:00Z",
            "expires_at": "2026-08-22T00:00:00Z",
            "packs": [
                {
                    "pack_id": PACK_ID,
                    "pack_type": "knowledge",
                    "version": version,
                    "board_id": BOARD_ID,
                    "url": pack_url,
                    "length": len(archive_bytes),
                    "sha256": hashlib.sha256(archive_bytes).hexdigest(),
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
        registry_bytes = json.dumps(registry, separators=(",", ":")).encode("utf-8") + b"\n"
        signature_bytes = self.private_key.sign(registry_bytes)
        signature = json.dumps(
            {
                "key_id": "test-official",
                "algorithm": "ed25519",
                "signature": base64.b64encode(signature_bytes).decode("ascii"),
            },
            separators=(",", ":"),
        ).encode("utf-8")
        self.transport.set(REGISTRY_URL, registry_bytes)
        self.transport.set(SIGNATURE_URL, signature)
        self.transport.set(pack_url, archive_bytes)

    def manager(self) -> PackManager:
        return PackManager(
            user_root=self.user_root,
            transport=self.transport,
            trust_store=self.trust_store,
            registry_url=REGISTRY_URL,
            signature_url=SIGNATURE_URL,
            core_version="0.1.0",
            now=NOW,
        )


class BoardContextTests(unittest.TestCase):
    def test_open_board_returns_summary_only_reverse_relationships(self):
        result = open_board(BOARD_ID, project_root=ROOT)

        self.assertTrue(result["success"], result)
        self.assertEqual(result["board"]["id"], BOARD_ID)
        self.assertTrue(result["components"])
        self.assertTrue(result["recipes"])
        self.assertNotIn("pins", result["components"][0])
        self.assertNotIn("wiring", result["recipes"][0])
        self.assertEqual(result["llmwiki"]["board_id"], BOARD_ID)

    def test_basic_led_canonical_path_hash_and_verification_snapshot_survive_pack_install_and_override(self):
        initial = get_catalog_record("basic-led", project_root=ROOT)
        initial_path = ROOT / initial["source_path"]
        initial_hash = hashlib.sha256(initial_path.read_bytes()).hexdigest()
        initial_snapshot, initial_digest = canonical_verification_snapshot(ROOT / "packs")

        with tempfile.TemporaryDirectory() as directory:
            fixture = SignedRegistryFixture(Path(directory))
            fixture.publish("1.0.0", "Official pack body.\n")
            manager = fixture.manager()
            manager.ensure(PACK_ID)
            official_resolver = ResourceResolver(
                user_root=fixture.user_root,
                builtin_root=Path(directory) / "builtin",
                manager=manager,
                environ={},
            )

            official = llmwiki_request(
                {
                    "action": "section",
                    "board_id": BOARD_ID,
                    "consumer": "chatmaker",
                    "section_id": "start-here",
                },
                manager=manager,
                resolver=official_resolver,
                project_root=ROOT,
            )

            override_root = Path(directory) / "overrides"
            override_path = override_root / PACK_ID / "llmwiki" / "sections" / "start-here.md"
            override_path.parent.mkdir(parents=True, exist_ok=True)
            override_path.write_text(page("Override body.\n"), encoding="utf-8", newline="\n")
            override_resolver = ResourceResolver(
                user_root=fixture.user_root,
                builtin_root=Path(directory) / "builtin",
                manager=manager,
                override_paths=[override_root],
                environ={},
            )
            override = llmwiki_request(
                {
                    "action": "section",
                    "board_id": BOARD_ID,
                    "consumer": "chatmaker",
                    "section_id": "start-here",
                },
                manager=manager,
                resolver=override_resolver,
                project_root=ROOT,
            )

        after = get_catalog_record("basic-led", project_root=ROOT)
        after_path = ROOT / after["source_path"]
        after_hash = hashlib.sha256(after_path.read_bytes()).hexdigest()
        after_snapshot, after_digest = canonical_verification_snapshot(ROOT / "packs")

        self.assertTrue(official["success"], official)
        self.assertEqual(official["provenance"]["kind"], "official_pack")
        self.assertTrue(override["success"], override)
        self.assertEqual(override["provenance"]["kind"], "local_override")
        self.assertEqual(
            override["provenance"]["path"],
            f"{PACK_ID}/llmwiki/sections/start-here.md",
        )
        self.assertEqual(after["source_path"], initial["source_path"])
        self.assertEqual(after_path, initial_path)
        self.assertEqual(after_hash, initial_hash)
        self.assertEqual(after_snapshot, initial_snapshot)
        self.assertEqual(after_digest, initial_digest)


if __name__ == "__main__":
    unittest.main()
