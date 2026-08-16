"""Installed-Core probe for automatic signed-pack fetch and offline reuse.

This file is executed with the Python interpreter from the clean-Core venv.  It
deliberately uses an in-memory transport and an ephemeral Ed25519 key: the
production private key and the network are never involved.
"""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from chatmaker.installers.pack_manager import FetchResponse, PackManager
from chatmaker.knowledge import execute_request
from chatmaker.resources import ResourceResolver


REGISTRY_URL = (
    "https://raw.githubusercontent.com/Amasun93/ChatMaker/main/"
    "distribution/registry/registry.json"
)
SIGNATURE_URL = REGISTRY_URL.replace("registry.json", "registry.sig.json")
PACK_ID = "chatmaker-board-arduino-nano-classic-knowledge"
BOARD_ID = "arduino-nano-classic"
NOW = datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc)


class MemoryTransport:
    def __init__(self, responses: dict[str, bytes]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def fetch(self, url: str) -> FetchResponse:
        self.calls.append(url)
        return FetchResponse(data=self.responses[url], final_url=url)


class OfflineTransport:
    def fetch(self, url: str) -> FetchResponse:
        raise AssertionError(f"cached offline read attempted a fetch: {url}")


def _fixture(pack_bytes: bytes) -> tuple[dict[str, object], dict[str, bytes]]:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    trust_store: dict[str, object] = {
        "schema_version": "1.0",
        "registry_url": REGISTRY_URL,
        "signature_url": SIGNATURE_URL,
        "keys": [
            {
                "key_id": "clean-core-fixture",
                "algorithm": "ed25519",
                "public_key_base64": base64.b64encode(public_key).decode("ascii"),
                "fingerprint_sha256": hashlib.sha256(public_key).hexdigest(),
                "status": "active",
                "not_before": "2026-08-01T00:00:00Z",
                "not_after": None,
            }
        ],
    }
    pack_url = (
        "https://raw.githubusercontent.com/Amasun93/ChatMaker/"
        "1111111111111111111111111111111111111111/distribution/packs/"
        "chatmaker-board-arduino-nano-classic-knowledge-1.0.0.cmpack"
    )
    registry = {
        "schema_version": "1.0",
        "sequence": 1,
        "generated_at": "2026-08-16T00:00:00Z",
        "expires_at": "2026-08-23T00:00:00Z",
        "packs": [
            {
                "pack_id": PACK_ID,
                "pack_type": "knowledge",
                "version": "1.0.0",
                "board_id": BOARD_ID,
                "url": pack_url,
                "length": len(pack_bytes),
                "sha256": hashlib.sha256(pack_bytes).hexdigest(),
                "compatibility": {
                    "core": {
                        "minimum": "0.1.0",
                        "maximum_exclusive": "0.2.0",
                    },
                    "pack_manifest_schema": ["1.0"],
                    "knowledge_index_schema": ["1.0"],
                },
            }
        ],
    }
    registry_bytes = (
        json.dumps(registry, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    detached = json.dumps(
        {
            "key_id": "clean-core-fixture",
            "algorithm": "ed25519",
            "signature": base64.b64encode(private_key.sign(registry_bytes)).decode("ascii"),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return trust_store, {
        REGISTRY_URL: registry_bytes,
        SIGNATURE_URL: detached,
        pack_url: pack_bytes,
    }


def _request() -> dict[str, str]:
    return {
        "action": "section",
        "board_id": BOARD_ID,
        "consumer": "chatduino",
        "section_id": "identify-and-safety",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--core-root", type=Path, required=True)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--user-root", type=Path, required=True)
    args = parser.parse_args()

    pack_bytes = args.pack.read_bytes()
    trust_store, responses = _fixture(pack_bytes)
    transport = MemoryTransport(responses)
    manager = PackManager(
        user_root=args.user_root,
        transport=transport,
        trust_store=trust_store,
        registry_url=REGISTRY_URL,
        signature_url=SIGNATURE_URL,
        core_version="0.1.0",
        now=NOW,
    )
    resolver = ResourceResolver(user_root=args.user_root, manager=manager)

    first = execute_request(
        _request(), manager=manager, resolver=resolver, project_root=args.core_root
    )
    first_calls = list(transport.calls)
    second = execute_request(
        _request(), manager=manager, resolver=resolver, project_root=args.core_root
    )
    second_calls = list(transport.calls)

    offline_manager = PackManager(
        user_root=args.user_root,
        transport=OfflineTransport(),
        trust_store=trust_store,
        registry_url=REGISTRY_URL,
        signature_url=SIGNATURE_URL,
        core_version="0.1.0",
        now=NOW,
    )
    offline = execute_request(
        _request(),
        manager=offline_manager,
        resolver=ResourceResolver(user_root=args.user_root, manager=offline_manager),
        project_root=args.core_root,
    )

    result = {
        "first_success": first.get("success"),
        "first_fetch_count": len(first_calls),
        "first_provenance": first.get("provenance"),
        "second_success": second.get("success"),
        "second_fetch_count": len(second_calls),
        "offline_success": offline.get("success"),
        "offline_provenance": offline.get("provenance"),
        "body_bytes": first.get("body_bytes"),
    }
    print(json.dumps(result, sort_keys=True))
    expected_provenance = {
        "kind": "official_pack",
        "pack_id": PACK_ID,
        "version": "1.0.0",
    }
    return 0 if (
        result["first_success"] is True
        and result["first_fetch_count"] == 3
        and result["first_provenance"] == expected_provenance
        and result["second_success"] is True
        and result["second_fetch_count"] == 3
        and result["offline_success"] is True
        and result["offline_provenance"] == expected_provenance
        and isinstance(result["body_bytes"], int)
        and result["body_bytes"] > 0
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
