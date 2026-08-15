from __future__ import annotations

import base64
import hashlib
import json
import re
import sys
import unittest
from pathlib import Path
from typing import Any

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.catalog import execute_request as catalog_request  # noqa: E402
from chatmaker.route import route_project_intent  # noqa: E402


PACK_BY_BOARD = {
    "arduino-nano-classic": "chatmaker-board-arduino-nano-classic-wiki",
    "arduino-uno-r3": "chatmaker-board-arduino-uno-r3-wiki",
    "esp32-devkit-v1": "chatmaker-board-esp32-devkit-v1-wiki",
}
SECTION_IDS = [
    "start-here",
    "identify-and-safety",
    "pins-and-electrical",
    "toolchains-and-upload",
    "components-and-wiring",
    "libraries-and-examples",
    "web-and-protocol",
    "troubleshooting",
]
REGISTRY_URL = (
    "https://raw.githubusercontent.com/Amasun93/ChatMaker/main/"
    "distribution/registry/registry.json"
)
SIGNATURE_URL = (
    "https://raw.githubusercontent.com/Amasun93/ChatMaker/main/"
    "distribution/registry/registry.sig.json"
)


def read_json(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def read_yaml(path: str) -> dict[str, Any]:
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def contract_example(name: str) -> Any:
    text = (ROOT / "docs/contracts/llmwiki-api-v1.md").read_text(encoding="utf-8")
    pattern = rf"<!-- contract:{re.escape(name)} -->\s*```json\s*(.*?)\s*```"
    match = re.search(pattern, text, flags=re.DOTALL)
    if match is None:
        raise AssertionError(f"missing JSON contract example: {name}")
    return json.loads(match.group(1))


def contains_key(value: Any, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(contains_key(item, key) for item in value)
    return False


class LlmWikiApiContractTests(unittest.TestCase):
    def test_index_request_and_success_payload_are_exact_and_cursorless(self):
        self.assertEqual(
            contract_example("index.request"),
            {
                "action": "index",
                "board_id": "arduino-nano-classic",
                "consumer": "chatduino",
            },
        )
        response = contract_example("index.success")
        self.assertEqual(
            set(response),
            {"success", "api_version", "action", "board_id", "consumer", "sections"},
        )
        self.assertTrue(response["success"])
        self.assertEqual(response["api_version"], "1")
        self.assertEqual(response["action"], "index")
        self.assertEqual(response["board_id"], "arduino-nano-classic")
        self.assertEqual(response["consumer"], "chatduino")
        self.assertEqual([item["section_id"] for item in response["sections"]], SECTION_IDS)
        self.assertTrue(
            all(
                item["pack_id"] == PACK_BY_BOARD["arduino-nano-classic"]
                for item in response["sections"]
            )
        )
        self.assertFalse(contains_key(response, "cursor"))

    def test_section_request_defaults_auto_install_and_returns_one_complete_bounded_body(self):
        self.assertEqual(
            contract_example("section.request"),
            {
                "action": "section",
                "board_id": "arduino-nano-classic",
                "consumer": "chatduino",
                "section_id": "identify-and-safety",
                "auto_install": True,
            },
        )
        response = contract_example("section.success")
        self.assertEqual(
            set(response),
            {
                "success",
                "api_version",
                "action",
                "board_id",
                "consumer",
                "section_id",
                "title",
                "body",
                "body_bytes",
                "max_body_bytes",
                "complete",
                "provenance",
            },
        )
        self.assertTrue(response["success"])
        self.assertEqual(response["action"], "section")
        self.assertEqual(response["section_id"], "identify-and-safety")
        self.assertEqual(response["body_bytes"], len(response["body"].encode("utf-8")))
        self.assertLessEqual(response["body_bytes"], response["max_body_bytes"])
        self.assertEqual(response["max_body_bytes"], 65536)
        self.assertTrue(response["complete"])
        self.assertEqual(
            response["provenance"],
            {
                "kind": "official_pack",
                "pack_id": "chatmaker-board-arduino-nano-classic-wiki",
                "version": "1.0.0",
            },
        )
        self.assertFalse(contains_key(response, "cursor"))

    def test_error_payload_has_stable_shape_and_never_guesses_a_board(self):
        response = contract_example("section.error")
        self.assertEqual(
            response,
            {
                "success": False,
                "api_version": "1",
                "action": "section",
                "board_id": "arduino-nano-clasic",
                "consumer": "chatduino",
                "section_id": "identify-and-safety",
                "error": {
                    "code": "llmwiki_board_not_found",
                    "message": "Unknown board_id: arduino-nano-clasic",
                    "retryable": False,
                },
            },
        )
        self.assertNotIn("suggested_board_id", response)
        self.assertFalse(contains_key(response, "cursor"))

    def test_error_codes_are_frozen_as_machine_readable_contract_data(self):
        self.assertEqual(
            contract_example("error.codes"),
            [
                "invalid_llmwiki_request",
                "unknown_llmwiki_action",
                "llmwiki_board_not_found",
                "llmwiki_consumer_not_supported",
                "llmwiki_section_not_found",
                "offline_pack_unavailable",
                "registry_fetch_failed",
                "registry_signature_invalid",
                "registry_key_unknown",
                "registry_key_retired",
                "registry_key_not_yet_valid",
                "registry_key_expired",
                "registry_expired",
                "registry_replay_detected",
                "pack_not_allowlisted",
                "pack_incompatible",
                "pack_download_failed",
                "pack_redirect_origin_changed",
                "pack_size_mismatch",
                "pack_hash_mismatch",
                "pack_archive_unsafe",
                "pack_manifest_invalid",
                "pack_content_invalid",
                "pack_drift_detected",
                "pack_activation_failed",
            ],
        )


class LlmWikiSchemaContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index_schema = read_yaml("packs/schemas/llmwiki-index.schema.yaml")
        cls.manifest_schema = read_json("packs/schemas/pack-manifest.schema.json")
        cls.registry_schema = read_json("packs/schemas/registry.schema.json")

    def valid_index(self, board_id: str) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "kind": "llmwiki-index",
            "board_id": board_id,
            "max_section_bytes": 65536,
            "sections": [
                {
                    "section_id": section_id,
                    "title": section_id.replace("-", " ").title(),
                    "summary": f"Bounded knowledge for {section_id}.",
                    "consumers": ["chatmaker", "chatduino", "chatweb"],
                    "topics": [section_id],
                    "pack_id": PACK_BY_BOARD[board_id],
                }
                for section_id in SECTION_IDS
            ],
        }

    def valid_manifest(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "format_version": 1,
            "pack_id": PACK_BY_BOARD["arduino-nano-classic"],
            "pack_version": "1.0.0",
            "pack_type": "knowledge",
            "board_id": "arduino-nano-classic",
            "compatibility": {
                "core": {"minimum": "0.1.0", "maximum_exclusive": "0.2.0"},
                "llmwiki_index_schema": ["1.0"],
            },
            "files": [
                {
                    "path": "llmwiki/index.yaml",
                    "length": 123,
                    "sha256": "a" * 64,
                },
                {
                    "path": "llmwiki/sections/identify-and-safety.md",
                    "length": 456,
                    "sha256": "b" * 64,
                },
            ],
        }

    def valid_registry(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "sequence": 1,
            "generated_at": "2026-08-16T00:00:00Z",
            "expires_at": "2026-08-23T00:00:00Z",
            "packs": [
                {
                    "pack_id": PACK_BY_BOARD["arduino-nano-classic"],
                    "pack_type": "knowledge",
                    "version": "1.0.0",
                    "board_id": "arduino-nano-classic",
                    "url": (
                        "https://raw.githubusercontent.com/Amasun93/ChatMaker/"
                        + "1" * 40
                        + "/distribution/packs/"
                        "chatmaker-board-arduino-nano-classic-wiki-1.0.0.cmpack"
                    ),
                    "length": 1024,
                    "sha256": "c" * 64,
                    "compatibility": {
                        "core": {"minimum": "0.1.0", "maximum_exclusive": "0.2.0"},
                        "pack_manifest_schema": ["1.0"],
                        "llmwiki_index_schema": ["1.0"],
                    },
                }
            ],
        }

    def test_each_board_index_maps_all_frozen_sections_to_its_exact_pack(self):
        for board_id, pack_id in PACK_BY_BOARD.items():
            with self.subTest(board_id=board_id):
                index = self.valid_index(board_id)
                jsonschema.Draft202012Validator(self.index_schema).validate(index)
                self.assertEqual([item["section_id"] for item in index["sections"]], SECTION_IDS)
                self.assertEqual({item["pack_id"] for item in index["sections"]}, {pack_id})

    def test_index_rejects_embedded_body_and_cursor(self):
        for forbidden in ("body", "cursor"):
            with self.subTest(forbidden=forbidden):
                index = self.valid_index("arduino-nano-classic")
                index["sections"][0][forbidden] = "not allowed"
                with self.assertRaises(jsonschema.ValidationError):
                    jsonschema.Draft202012Validator(self.index_schema).validate(index)

    def test_manifest_accepts_only_passive_llmwiki_files(self):
        manifest = self.valid_manifest()
        jsonschema.Draft202012Validator(self.manifest_schema).validate(manifest)

        for field in ("hooks", "dependencies"):
            with self.subTest(field=field):
                invalid = dict(manifest)
                invalid[field] = []
                with self.assertRaises(jsonschema.ValidationError):
                    jsonschema.Draft202012Validator(self.manifest_schema).validate(invalid)

        invalid = self.valid_manifest()
        invalid["files"][0]["path"] = "boards/arduino-nano-classic.yaml"
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(self.manifest_schema).validate(invalid)

    def test_registry_requires_immutable_commit_pinned_pack_urls(self):
        registry = self.valid_registry()
        jsonschema.Draft202012Validator(self.registry_schema).validate(registry)

        registry["packs"][0]["url"] = registry["packs"][0]["url"].replace(
            "1" * 40, "main"
        )
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(self.registry_schema).validate(registry)

    def test_detached_signature_shape_is_keyed_ed25519_over_raw_registry_bytes(self):
        signature_schema = self.registry_schema["$defs"]["detachedSignature"]
        valid = {
            "key_id": "chatmaker-official-2026-01",
            "algorithm": "ed25519",
            "signature": "A" * 86 + "==",
        }
        jsonschema.Draft202012Validator(signature_schema).validate(valid)
        invalid = dict(valid, algorithm="rsa-pss")
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(signature_schema).validate(invalid)

    def test_all_new_schemas_are_valid_draft_2020_12_schemas(self):
        for schema in (self.index_schema, self.manifest_schema, self.registry_schema):
            jsonschema.Draft202012Validator.check_schema(schema)


class DistributionAndCompatibilityContractTests(unittest.TestCase):
    def test_checked_in_anchor_matches_the_preflight_public_identity_and_urls(self):
        anchors = read_json("runtime/chatmaker/trust/official_registry_keys.json")
        self.assertEqual(anchors["registry_url"], REGISTRY_URL)
        self.assertEqual(anchors["signature_url"], SIGNATURE_URL)
        self.assertEqual(
            anchors["keys"],
            [
                {
                    "key_id": "chatmaker-official-2026-01",
                    "algorithm": "ed25519",
                    "public_key_base64": "ibJcQjKeXe/5ZmIaEV9HmIO3j9PbVhDzSlYA9Oj9Hak=",
                    "fingerprint_sha256": (
                        "70570b179cf452abcc7486f76a408a25faee3702433663e99b7418498d725f67"
                    ),
                    "status": "active",
                    "not_before": "2026-08-16T00:00:00Z",
                    "not_after": None,
                }
            ],
        )
        public_key = base64.b64decode(anchors["keys"][0]["public_key_base64"], validate=True)
        self.assertEqual(len(public_key), 32)
        self.assertEqual(
            hashlib.sha256(public_key).hexdigest(),
            anchors["keys"][0]["fingerprint_sha256"],
        )

    def test_canonical_ids_counts_and_legacy_catalog_shapes_remain_unchanged(self):
        ids_by_kind = {}
        for kind, folder in {
            "board": "boards",
            "component": "components",
            "recipe": "recipes",
        }.items():
            ids_by_kind[kind] = [
                read_yaml(str(path.relative_to(ROOT)))["id"]
                for path in sorted((ROOT / "packs" / folder).glob("*.yaml"))
            ]
        self.assertEqual(
            ids_by_kind["board"],
            ["arduino-nano-classic", "arduino-uno-r3", "esp32-devkit-v1"],
        )
        self.assertEqual(
            ids_by_kind["component"],
            [
                "active-buzzer-module",
                "analog-light-sensor-module",
                "basic-led",
                "common-cathode-rgb-led",
                "dht11-three-pin-module",
                "hc-sr04",
                "linear-potentiometer-10k",
                "momentary-button-two-pin",
                "one-channel-relay-module-5v",
                "sg90-micro-servo",
                "ssd1306-i2c-128x64-module",
                "ws2812b-addressable-rgb",
            ],
        )
        self.assertEqual(
            ids_by_kind["recipe"],
            [
                "blink-external-led",
                "esp32-ap-led-sensor",
                "esp32-external-led-blink",
                "nano-blink-built-in",
                "nano-dht11-serial",
                "nano-light-led",
                "nano-oled-light",
                "nano-potentiometer-led",
                "nano-relay-control-side",
                "nano-rgb-led-cycle",
                "nano-servo-button",
                "nano-ultrasonic-buzzer",
                "nano-ws2812-one-pixel",
                "uno-blink-built-in",
            ],
        )

        canonical_verification = []
        for kind, folder in {
            "board": "boards",
            "component": "components",
            "recipe": "recipes",
        }.items():
            for path in sorted((ROOT / "packs" / folder).glob("*.yaml")):
                record = read_yaml(str(path.relative_to(ROOT)))
                canonical_verification.append(
                    {"kind": kind, "id": record["id"], "verification": record["verification"]}
                )
        digest = hashlib.sha256(
            json.dumps(
                canonical_verification,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(
            digest,
            "771fdc359df57403aaaae198cb5ead97a7ced113318f5a33478743fec9f9b280",
        )

        search = catalog_request({"action": "search", "query": "basic-led", "limit": 1})
        self.assertEqual(
            set(search),
            {"success", "action", "query", "kind", "match_count", "matches"},
        )
        self.assertEqual(
            set(search["matches"][0]),
            {"id", "kind", "name", "aliases", "category", "interface", "summary", "verification"},
        )
        get = catalog_request({"action": "get", "id": "basic-led"})
        self.assertEqual(set(get), {"success", "action", "record", "source_path"})

    def test_cad_intent_is_rejected_without_a_chatcad_specialist(self):
        result = route_project_intent({"cad": {"outcome": "mounting bracket"}})
        self.assertFalse(result["success"])
        self.assertEqual(result["route"], "clarify")
        self.assertEqual(result["status"], "blocked")
        self.assertNotIn("chatcad", result["specialists"])


if __name__ == "__main__":
    unittest.main()
