from __future__ import annotations

import base64
import hashlib
import io
import json
import re
import sys
import tempfile
import threading
import unittest
import zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import yaml

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.knowledge import execute_request
from chatmaker.knowledge_semantics import (
    BOARD_IDS,
    KnowledgeSemanticError,
    PACK_IDS,
    SECTION_IDS,
    validate_index_bytes,
    validate_pack_payload,
    validate_page_bytes,
)
from chatmaker.installers import pack_artifact, pack_manager, registry
from chatmaker.installers.pack_artifact import PackArtifactError, build_pack
from chatmaker.installers.pack_manager import FetchResponse, PackManager, PackManagerError
from chatmaker.resources import ResourceIntegrityError, ResourceResolver


BOARD_ID = "arduino-nano-classic"
PACK_ID = "chatmaker-board-arduino-nano-classic-knowledge"
REGISTRY_URL = "https://example.invalid/registry.json"
SIGNATURE_URL = "https://example.invalid/registry.sig.json"
NOW = datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc)


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

    def put(
        self,
        pack_id: str,
        path: str,
        data: bytes,
        *,
        provenance: dict | None = None,
    ) -> None:
        self.values[(pack_id, path)] = (
            data,
            provenance
            or {"kind": "official_pack", "pack_id": pack_id, "version": "1.0.0"},
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


class DriftResolver(RecordingResolver):
    def __init__(self) -> None:
        super().__init__()
        self.drifting: set[tuple[str, str]] = set()

    def put_drifting(self, pack_id: str, path: str) -> None:
        self.put(pack_id, path, b"drift")
        self.drifting.add((pack_id, path))

    def resolve(self, path: str, *, pack_id: str | None = None) -> FakeResolved:
        resolved = super().resolve(path, pack_id=pack_id)
        assert pack_id is not None
        if (pack_id, path) not in self.drifting:
            return resolved

        resolver = self

        class DriftingResource(FakeResolved):
            def read_bytes(self) -> bytes:
                resolver.reads.append(self.key)
                raise ResourceIntegrityError(
                    "sha256_mismatch",
                    path=Path("drifted-resource"),
                    provenance=self.provenance,
                )

        return DriftingResource(self, resolved.key, resolved.data, resolved.provenance)


class RepairingManager:
    def __init__(self, resolver: DriftResolver) -> None:
        self.resolver = resolver
        self.ensure_calls: list[str] = []
        self.quarantine_calls: list[tuple[str, str]] = []

    def ensure(self, pack_id: str) -> None:
        self.ensure_calls.append(pack_id)
        self.resolver.drifting.discard((pack_id, "knowledge/sections/start-here.md"))
        self.resolver.put(
            pack_id,
            "knowledge/sections/start-here.md",
            page("start-here", "Repaired official guidance.\n"),
        )

    def quarantine_active_drift(self, pack_id: str, *, version: str) -> None:
        self.quarantine_calls.append((pack_id, version))


class MemoryTransport:
    def __init__(self) -> None:
        self.responses: dict[str, tuple[bytes, str] | BaseException] = {}
        self.calls: list[str] = []
        self.lock = threading.Lock()

    def set(self, url: str, data: bytes, *, final_url: str | None = None) -> None:
        self.responses[url] = (data, final_url or url)

    def fetch(self, url: str) -> FetchResponse:
        with self.lock:
            self.calls.append(url)
            response = self.responses[url]
        if isinstance(response, BaseException):
            raise response
        data, final_url = response
        return FetchResponse(data=data, final_url=final_url)


class KnowledgeSignedRegistryFixture:
    def __init__(self, root: Path) -> None:
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
            "keys": [{
                "key_id": "test-official",
                "algorithm": "ed25519",
                "public_key_base64": base64.b64encode(public).decode("ascii"),
                "fingerprint_sha256": hashlib.sha256(public).hexdigest(),
                "status": "active",
                "not_before": "2026-08-01T00:00:00Z",
                "not_after": None,
            }],
        }

    def archive(self, version: str, body: str) -> bytes:
        source = self.root / "source" / version
        sections = source / "knowledge" / "sections"
        sections.mkdir(parents=True, exist_ok=True)
        (source / "knowledge" / "index.yaml").write_text(
            yaml.safe_dump(index_payload(), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        for section_id in SECTION_IDS:
            (sections / f"{section_id}.md").write_bytes(
                page(section_id, body if section_id == "start-here" else "Complete guidance.\n")
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

    def publish(self, version: str, sequence: int, body: str, *, corrupt: bool = False) -> str:
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
            "packs": [{
                "pack_id": PACK_ID,
                "pack_type": "knowledge",
                "version": version,
                "board_id": BOARD_ID,
                "url": pack_url,
                "length": len(archive),
                "sha256": hashlib.sha256(archive).hexdigest(),
                "compatibility": {
                    "core": {"minimum": "0.1.0", "maximum_exclusive": "0.2.0"},
                    "pack_manifest_schema": ["1.0"],
                    "llmwiki_index_schema": ["1.0"],
                },
            }],
        }
        raw = json.dumps(registry, separators=(",", ":")).encode("utf-8") + b"\n"
        signature = self.private_key.sign(raw)
        if corrupt:
            signature = bytes([signature[0] ^ 1]) + signature[1:]
        detached = json.dumps({
            "key_id": "test-official",
            "algorithm": "ed25519",
            "signature": base64.b64encode(signature).decode("ascii"),
        }, separators=(",", ":")).encode("utf-8")
        self.transport.set(REGISTRY_URL, raw)
        self.transport.set(SIGNATURE_URL, detached)
        self.transport.set(pack_url, archive)
        return pack_url

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

    @contextmanager
    def knowledge_pack_format(self):
        """Use the new payload contract only inside this migration test fixture."""

        original_manifest_schema = pack_artifact._manifest_schema
        registry_schema = json.loads(registry._REGISTRY_SCHEMA_PATH.read_text(encoding="utf-8"))
        registry_schema["$defs"]["packId"]["enum"].append(PACK_ID)
        registry_schema["$defs"]["pack"]["properties"]["url"]["pattern"] = (
            registry_schema["$defs"]["pack"]["properties"]["url"]["pattern"].replace(
                "-wiki-", "-knowledge-"
            )
        )
        for condition in registry_schema["$defs"]["pack"]["allOf"]:
            if condition["if"]["properties"]["board_id"]["const"] == BOARD_ID:
                condition["then"]["properties"]["pack_id"]["const"] = PACK_ID
        registry_schema_path = self.root / "schemas" / "registry.schema.json"
        registry_schema_path.parent.mkdir(parents=True, exist_ok=True)
        registry_schema_path.write_text(
            json.dumps(registry_schema, separators=(",", ":")), encoding="utf-8"
        )

        def manifest_schema() -> dict:
            schema = original_manifest_schema()
            schema["properties"]["pack_id"]["enum"].append(PACK_ID)
            files = schema["properties"]["files"]
            files["contains"]["properties"]["path"]["const"] = "knowledge/index.yaml"
            files["items"]["properties"]["path"]["pattern"] = (
                r"^knowledge/(?:index\.yaml|sections/[a-z0-9][a-z0-9-]*\.md)$"
            )
            for condition in schema["allOf"]:
                if condition["if"]["properties"]["board_id"]["const"] == BOARD_ID:
                    condition["then"]["properties"]["pack_id"]["const"] = PACK_ID
            return schema

        def source_files(root: Path) -> list[tuple[str, bytes]]:
            return sorted(
                (
                    (path.relative_to(root).as_posix(), path.read_bytes())
                    for path in root.rglob("*")
                    if path.is_file()
                ),
                key=lambda item: item[0],
            )

        def validate_knowledge_payload(files, *, board_id: str, pack_id: str):
            try:
                return validate_pack_payload(
                    files,
                    expected_board_id=board_id,
                    expected_pack_id=pack_id,
                )
            except KnowledgeSemanticError as exc:
                raise PackArtifactError(
                    "pack_content_invalid", reason=exc.reason, path=exc.path
                ) from exc

        def validate_archive(source, **_kwargs):
            raw = source if isinstance(source, bytes) else Path(source).read_bytes()
            with zipfile.ZipFile(io.BytesIO(raw), "r") as archive:
                manifest_raw = archive.read("pack-manifest.json")
                manifest = pack_artifact._validate_manifest(json.loads(manifest_raw))
                files = {item["path"]: archive.read(item["path"]) for item in manifest["files"]}
            validate_knowledge_payload(
                files,
                board_id=manifest["board_id"],
                pack_id=manifest["pack_id"],
            )
            return manifest

        def validate_staging(staging_dir, manifest):
            root = Path(staging_dir)
            manifest = pack_artifact._validate_manifest(dict(manifest))
            files = {
                item["path"]: (root / item["path"]).read_bytes()
                for item in manifest["files"]
            }
            validate_knowledge_payload(
                files,
                board_id=manifest["board_id"],
                pack_id=manifest["pack_id"],
            )
            return manifest

        def extract_archive(source, staging_dir, **_kwargs):
            raw = source if isinstance(source, bytes) else Path(source).read_bytes()
            manifest = validate_archive(raw)
            target = Path(staging_dir)
            target.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(raw), "r") as archive:
                for path in ["pack-manifest.json", *(item["path"] for item in manifest["files"])]:
                    destination = target / path
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(archive.read(path))
            return validate_staging(target, manifest)

        with (
            mock.patch.object(pack_artifact, "_source_files", source_files),
            mock.patch.object(pack_artifact, "_manifest_schema", manifest_schema),
            mock.patch.object(
                pack_artifact,
                "_PAYLOAD_PATTERN",
                re.compile(r"^knowledge/(?:index\.yaml|sections/[a-z0-9][a-z0-9-]*\.md)$"),
            ),
            mock.patch.object(
                pack_artifact,
                "_validate_llmwiki_payload",
                validate_knowledge_payload,
            ),
            mock.patch.dict(pack_manager.ALLOWED_PACKS, {PACK_ID: BOARD_ID}),
            mock.patch.object(pack_manager, "validate_pack_archive", validate_archive),
            mock.patch.object(pack_manager, "validate_staging", validate_staging),
            mock.patch.object(pack_manager, "extract_validated_pack", extract_archive),
            mock.patch.object(
                registry,
                "_ALLOWED_PACK_IDS",
                {*registry._ALLOWED_PACK_IDS, PACK_ID},
            ),
            mock.patch.object(
                registry,
                "_PACK_URL_PATTERN",
                re.compile(
                    r"^https://raw\.githubusercontent\.com/Amasun93/ChatMaker/"
                    r"[0-9a-f]{40}/distribution/packs/chatmaker-board-"
                    r"(?:arduino-nano-classic|arduino-uno-r3|esp32-devkit-v1)"
                    r"-knowledge-[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?\.cmpack$"
                ),
            ),
            mock.patch.object(registry, "_REGISTRY_SCHEMA_PATH", registry_schema_path),
        ):
            yield


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

    def test_reader_rejects_wrong_board_and_duplicate_frontmatter_identity(self):
        malformed = page("start-here", "Wrong board.\n").replace(
            f"board_id: {BOARD_ID}\n".encode("utf-8"),
            b"board_id: arduino-uno-r3\n",
            1,
        )
        duplicate = page("start-here", "Ambiguous identity.\n").replace(
            f"stable_id: {BOARD_ID}-start-here\n".encode("utf-8"),
            b"stable_id: attacker-controlled\nstable_id: arduino-nano-classic-start-here\n",
            1,
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_index(root)
            for raw in (malformed, duplicate):
                with self.subTest(raw=raw[:32]):
                    resolver = RecordingResolver()
                    resolver.put(PACK_ID, "knowledge/sections/start-here.md", raw)
                    result = self.request(
                        {
                            "action": "section",
                            "board_id": BOARD_ID,
                            "consumer": "chatduino",
                            "section_id": "start-here",
                        },
                        root=root,
                        resolver=resolver,
                    )
                    self.assertFalse(result["success"])
                    self.assertEqual(result["error"]["code"], "pack_content_invalid")

    def test_reader_enforces_body_limit_after_frontmatter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_index(root)
            boundary = RecordingResolver()
            boundary.put(
                PACK_ID,
                "knowledge/sections/start-here.md",
                page("start-here", "a" * 65_536),
            )
            accepted = self.request(
                {
                    "action": "section",
                    "board_id": BOARD_ID,
                    "consumer": "chatduino",
                    "section_id": "start-here",
                },
                root=root,
                resolver=boundary,
            )
            oversized = RecordingResolver()
            oversized.put(
                PACK_ID,
                "knowledge/sections/start-here.md",
                page("start-here", "a" * 65_537),
            )
            rejected = self.request(
                {
                    "action": "section",
                    "board_id": BOARD_ID,
                    "consumer": "chatduino",
                    "section_id": "start-here",
                },
                root=root,
                resolver=oversized,
            )

        self.assertTrue(accepted["success"], accepted)
        self.assertEqual(accepted["body_bytes"], 65_536)
        self.assertEqual(accepted["body"], "a" * 65_536)
        self.assertFalse(rejected["success"])
        self.assertEqual(rejected["error"]["code"], "pack_content_invalid")

    def test_official_drift_is_quarantined_and_repaired_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_index(root)
            resolver = DriftResolver()
            resolver.put_drifting(PACK_ID, "knowledge/sections/start-here.md")
            manager = RepairingManager(resolver)

            result = self.request(
                {
                    "action": "section",
                    "board_id": BOARD_ID,
                    "consumer": "chatduino",
                    "section_id": "start-here",
                },
                root=root,
                manager=manager,
                resolver=resolver,
            )

        self.assertTrue(result["success"], result)
        self.assertEqual(result["body"], "Repaired official guidance.\n")
        self.assertEqual(manager.quarantine_calls, [(PACK_ID, "1.0.0")])
        self.assertEqual(manager.ensure_calls, [PACK_ID])
        self.assertEqual(len(resolver.reads), 2)

    def test_invalid_local_override_is_not_repaired_or_quarantined(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_index(root)
            resolver = DriftResolver()
            resolver.put(
                PACK_ID,
                "knowledge/sections/start-here.md",
                b"local experiment without frontmatter",
                provenance={"kind": "local_override", "path": "experiment/start-here.md"},
            )
            manager = RepairingManager(resolver)

            result = self.request(
                {
                    "action": "section",
                    "board_id": BOARD_ID,
                    "consumer": "chatduino",
                    "section_id": "start-here",
                },
                root=root,
                manager=manager,
                resolver=resolver,
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["error"]["code"], "pack_content_invalid")
        self.assertEqual(manager.quarantine_calls, [])
        self.assertEqual(manager.ensure_calls, [])

    def test_cached_official_body_reads_without_reinstalling(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_index(root)
            resolver = DriftResolver()
            resolver.put(
                PACK_ID,
                "knowledge/sections/start-here.md",
                page("start-here", "Cached official guidance.\n"),
            )
            manager = RepairingManager(resolver)
            request = {
                "action": "section",
                "board_id": BOARD_ID,
                "consumer": "chatduino",
                "section_id": "start-here",
            }

            first = self.request(request, root=root, manager=manager, resolver=resolver)
            second = self.request(request, root=root, manager=manager, resolver=resolver)

        self.assertTrue(first["success"], first)
        self.assertTrue(second["success"], second)
        self.assertEqual(manager.ensure_calls, [])
        self.assertEqual(first["body"], "Cached official guidance.\n")

    def test_signed_download_is_cached_offline_and_bad_updates_preserve_active_knowledge(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_index(root)
            fixture = KnowledgeSignedRegistryFixture(root)
            with fixture.knowledge_pack_format():
                pack_url = fixture.publish("1.0.0", 1, "Cached official guidance.\n")
                manager = fixture.manager()
                resolver = ResourceResolver(
                    user_root=fixture.user_root,
                    builtin_root=root / "builtin",
                    manager=manager,
                    environ={},
                )
                request = {
                    "action": "section",
                    "board_id": BOARD_ID,
                    "consumer": "chatduino",
                    "section_id": "start-here",
                }

                first = self.request(request, root=root, manager=manager, resolver=resolver)
                calls_after_first = list(fixture.transport.calls)
                fixture.transport.responses = {
                    url: AssertionError(f"offline read attempted {url}")
                    for url in fixture.transport.responses
                }
                offline = self.request(request, root=root, manager=manager, resolver=resolver)
                calls_after_offline = list(fixture.transport.calls)
                fixture.publish("1.1.0", 2, "Replacement guidance.\n", corrupt=True)
                with self.assertRaises(PackManagerError) as bad_update:
                    manager.update(PACK_ID)
                after_bad_update = self.request(
                    request,
                    root=root,
                    manager=manager,
                    resolver=resolver,
                )

        self.assertTrue(first["success"], first)
        self.assertTrue(offline["success"], offline)
        self.assertTrue(after_bad_update["success"], after_bad_update)
        self.assertEqual(calls_after_offline, calls_after_first)
        self.assertEqual(calls_after_first.count(pack_url), 1)
        self.assertEqual(bad_update.exception.code, "registry_signature_invalid")
        self.assertEqual(after_bad_update["body"], "Cached official guidance.\n")

    def test_real_resource_resolver_reads_only_the_selected_section(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_index(root)
            builtin = root / "builtin"
            section_root = builtin / PACK_ID / "knowledge" / "sections"
            section_root.mkdir(parents=True)
            (section_root / "start-here.md").write_bytes(
                page("start-here", "Selected body.\n")
            )
            (section_root / "troubleshooting.md").write_bytes(b"invalid unused body")
            resolver = ResourceResolver(
                user_root=root / "user",
                builtin_root=builtin,
                environ={},
            )

            result = self.request(
                {
                    "action": "section",
                    "board_id": BOARD_ID,
                    "consumer": "chatduino",
                    "section_id": "start-here",
                },
                root=root,
                resolver=resolver,
            )

        self.assertTrue(result["success"], result)
        self.assertEqual(result["body"], "Selected body.\n")
        self.assertEqual(result["provenance"]["kind"], "builtin_core")

    def test_reader_rejects_crlf_knowledge_page(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_index(root)
            resolver = RecordingResolver()
            resolver.put(
                PACK_ID,
                "knowledge/sections/start-here.md",
                page("start-here", "LF-only is part of the format.\n").replace(b"\n", b"\r\n"),
            )

            result = self.request(
                {
                    "action": "section",
                    "board_id": BOARD_ID,
                    "consumer": "chatduino",
                    "section_id": "start-here",
                },
                root=root,
                resolver=resolver,
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["error"]["code"], "pack_content_invalid")


if __name__ == "__main__":
    unittest.main()
