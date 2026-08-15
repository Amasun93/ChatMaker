from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

try:
    from chatmaker.installers import registry
except (ImportError, ModuleNotFoundError):
    registry = None


REGISTRY_URL = (
    "https://raw.githubusercontent.com/Amasun93/ChatMaker/main/"
    "distribution/registry/registry.json"
)
PACK_URL = (
    "https://raw.githubusercontent.com/Amasun93/ChatMaker/"
    + "1" * 40
    + "/distribution/packs/"
    "chatmaker-board-arduino-nano-classic-wiki-1.0.0.cmpack"
)
NOW = datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc)


class RegistryVerificationTests(unittest.TestCase):
    def setUp(self):
        if registry is None:
            self.fail("Task 3 registry module is missing")
        self.private_key = Ed25519PrivateKey.generate()
        public_bytes = self.private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        self.key_id = "test-official-2026-01"
        self.trust_store = {
            "schema_version": "1.0",
            "registry_url": REGISTRY_URL,
            "signature_url": REGISTRY_URL.replace("registry.json", "registry.sig.json"),
            "keys": [
                {
                    "key_id": self.key_id,
                    "algorithm": "ed25519",
                    "public_key_base64": base64.b64encode(public_bytes).decode("ascii"),
                    "fingerprint_sha256": hashlib.sha256(public_bytes).hexdigest(),
                    "status": "active",
                    "not_before": "2026-08-16T00:00:00Z",
                    "not_after": None,
                }
            ],
        }
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.state_path = Path(self.tempdir.name) / "registry-sequences.json"

    def registry_value(self, *, sequence: int = 7) -> dict:
        return {
            "schema_version": "1.0",
            "sequence": sequence,
            "generated_at": "2026-08-18T00:00:00Z",
            "expires_at": "2026-08-25T00:00:00Z",
            "packs": [
                {
                    "pack_id": "chatmaker-board-arduino-nano-classic-wiki",
                    "pack_type": "knowledge",
                    "version": "1.0.0",
                    "board_id": "arduino-nano-classic",
                    "url": PACK_URL,
                    "length": 3,
                    "sha256": hashlib.sha256(b"zip").hexdigest(),
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

    def signed(self, value: dict) -> tuple[bytes, bytes]:
        registry_bytes = json.dumps(value, separators=(",", ":")).encode("utf-8") + b"\n"
        signature = base64.b64encode(self.private_key.sign(registry_bytes)).decode("ascii")
        detached = {
            "key_id": self.key_id,
            "algorithm": "ed25519",
            "signature": signature,
        }
        return registry_bytes, json.dumps(detached).encode("utf-8")

    def verify(self, registry_bytes: bytes, signature_bytes: bytes, **overrides):
        kwargs = {
            "registry_url": REGISTRY_URL,
            "trust_store": self.trust_store,
            "state_path": self.state_path,
            "now": NOW,
        }
        kwargs.update(overrides)
        return registry.verify_registry(registry_bytes, signature_bytes, **kwargs)

    def assert_code(self, expected: str, call, *args, **kwargs):
        with self.assertRaises(registry.RegistryError) as caught:
            call(*args, **kwargs)
        self.assertEqual(caught.exception.code, expected)
        return caught.exception

    def test_verifies_exact_raw_bytes_and_persists_sequence_atomically(self):
        registry_bytes, signature_bytes = self.signed(self.registry_value())
        result = self.verify(registry_bytes, signature_bytes)
        self.assertEqual(result["sequence"], 7)
        self.assertEqual(result["key_id"], self.key_id)
        self.assertEqual(result["registry"]["packs"][0]["url"], PACK_URL)
        persisted = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.assertEqual(
            persisted,
            {
                "schema_version": "1.0",
                "sequences": [
                    {
                        "registry_url": REGISTRY_URL,
                        "key_id": self.key_id,
                        "highest_sequence": 7,
                    }
                ],
            },
        )
        self.assertEqual(list(self.state_path.parent.glob("*.tmp")), [])

        altered = registry_bytes.replace(b'"sequence":7', b'"sequence":8')
        self.assert_code(
            "registry_signature_invalid",
            self.verify,
            altered,
            signature_bytes,
            state_path=Path(self.tempdir.name) / "other-state.json",
        )

    def test_restart_rejects_equal_and_decreasing_sequence_as_replay(self):
        first = self.signed(self.registry_value(sequence=7))
        self.verify(*first)
        for sequence in (7, 6):
            with self.subTest(sequence=sequence):
                self.assert_code(
                    "registry_replay_detected",
                    self.verify,
                    *self.signed(self.registry_value(sequence=sequence)),
                )

    def test_rejects_unknown_retired_and_out_of_window_keys(self):
        registry_bytes, signature_bytes = self.signed(self.registry_value())

        unknown = json.loads(signature_bytes)
        unknown["key_id"] = "unknown-key"
        self.assert_code(
            "registry_key_unknown",
            self.verify,
            registry_bytes,
            json.dumps(unknown).encode(),
        )

        cases = [
            ("retired", "2026-08-16T00:00:00Z", None, "registry_key_retired"),
            ("active", "2026-08-19T00:00:00Z", None, "registry_key_not_yet_valid"),
            (
                "active",
                "2026-08-16T00:00:00Z",
                "2026-08-18T11:59:59Z",
                "registry_key_expired",
            ),
        ]
        for status, not_before, not_after, expected in cases:
            with self.subTest(expected=expected):
                store = json.loads(json.dumps(self.trust_store))
                store["keys"][0].update(
                    status=status,
                    not_before=not_before,
                    not_after=not_after,
                )
                self.assert_code(
                    expected,
                    self.verify,
                    registry_bytes,
                    signature_bytes,
                    trust_store=store,
                )

    def test_rejects_malformed_noncanonical_and_bad_signatures(self):
        registry_bytes, signature_bytes = self.signed(self.registry_value())
        valid = json.loads(signature_bytes)
        cases = [
            b"not-json",
            json.dumps({**valid, "algorithm": "rsa"}).encode(),
            json.dumps({**valid, "extra": True}).encode(),
            json.dumps({**valid, "signature": "A" * 85 + "B=="}).encode(),
            json.dumps({**valid, "signature": base64.b64encode(b"x" * 64).decode()}).encode(),
        ]
        for detached in cases:
            with self.subTest(detached=detached[:30]):
                self.assert_code(
                    "registry_signature_invalid",
                    self.verify,
                    registry_bytes,
                    detached,
                )

    def test_rejects_expired_and_future_registry(self):
        expired = self.registry_value()
        expired["expires_at"] = "2026-08-18T11:59:59Z"
        future = self.registry_value()
        future["generated_at"] = "2026-08-18T12:00:01Z"
        for value, reason in ((expired, "expired"), (future, "generated_at_in_future")):
            with self.subTest(reason=reason):
                error = self.assert_code(
                    "registry_expired",
                    self.verify,
                    *self.signed(value),
                )
                self.assertEqual(error.reason, reason)

    def test_rejects_non_allowlisted_registry_and_mutable_pack_url(self):
        signed = self.signed(self.registry_value())
        self.assert_code(
            "registry_fetch_failed",
            self.verify,
            *signed,
            registry_url="https://example.invalid/registry.json",
        )

        mutable = self.registry_value()
        mutable["packs"][0]["url"] = PACK_URL.replace("1" * 40, "main")
        self.assert_code(
            "pack_content_invalid",
            self.verify,
            *self.signed(mutable),
        )

        unknown_pack = self.registry_value()
        unknown_pack["packs"][0]["pack_id"] = "third-party-executable"
        self.assert_code(
            "pack_not_allowlisted",
            self.verify,
            *self.signed(unknown_pack),
        )

    def test_transport_metadata_rejects_registry_or_signature_origin_change(self):
        signed = self.signed(self.registry_value())
        for overrides in (
            {"final_registry_url": "https://example.invalid/registry.json"},
            {
                "signature_url": self.trust_store["signature_url"],
                "final_signature_url": "https://example.invalid/registry.sig.json",
            },
        ):
            with self.subTest(overrides=overrides):
                error = self.assert_code(
                    "registry_fetch_failed",
                    self.verify,
                    *signed,
                    **overrides,
                )
                self.assertEqual(error.reason, "redirect_origin_changed")

        accepted = self.verify(
            *signed,
            final_registry_url=REGISTRY_URL + "?transport=metadata",
            signature_url=self.trust_store["signature_url"],
            final_signature_url=self.trust_store["signature_url"] + "?transport=metadata",
        )
        self.assertEqual(accepted["sequence"], 7)

    def test_redirect_origin_and_pack_length_hash_fail_closed(self):
        pack = self.registry_value()["packs"][0]
        self.assertEqual(registry.verify_pack_download(pack, b"zip"), b"zip")
        self.assert_code(
            "pack_redirect_origin_changed",
            registry.verify_pack_download,
            pack,
            b"zip",
            final_url="https://objects.example.invalid/archive.cmpack",
        )
        self.assert_code("pack_size_mismatch", registry.verify_pack_download, pack, b"zi")
        self.assert_code("pack_hash_mismatch", registry.verify_pack_download, pack, b"bad")

    def test_failure_boundaries_preserve_or_commit_monotonic_state(self):
        signed = self.signed(self.registry_value())

        def fail_before(name: str):
            if name == "registry.before_sequence_replace":
                raise RuntimeError("injected")

        error = self.assert_code(
            "registry_fetch_failed",
            self.verify,
            *signed,
            failure_injector=fail_before,
        )
        self.assertEqual(error.reason, "failure_injected")
        self.assertFalse(self.state_path.exists())

        def fail_after(name: str):
            if name == "registry.after_sequence_replace":
                raise RuntimeError("injected")

        error = self.assert_code(
            "registry_fetch_failed",
            self.verify,
            *signed,
            failure_injector=fail_after,
        )
        self.assertEqual(error.reason, "failure_injected")
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["sequences"][0]["highest_sequence"], 7)

    def test_phase_contract_names_are_frozen_for_later_manager(self):
        self.assertEqual(
            registry.VERIFICATION_PHASES,
            {
                "registry_bytes_fetched": "registry.bytes_fetched",
                "signature_verified": "registry.signature_verified",
                "archive_downloaded": "pack.after_part_write",
                "archive_hash_verified": "pack.after_archive_verify",
                "staging_extracted": "pack.after_staging_extract",
                "staging_validated": "pack.after_staging_validate",
            },
        )


class RegistrySigningScriptTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        self.private_key = Ed25519PrivateKey.generate()
        self.private_path = self.root / "private.pem"
        self.private_path.write_bytes(
            self.private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        public_bytes = self.private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        self.trust_path = self.root / "trust.json"
        self.trust_path.write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "registry_url": REGISTRY_URL,
                    "signature_url": REGISTRY_URL.replace("registry.json", "registry.sig.json"),
                    "keys": [
                        {
                            "key_id": "test-key",
                            "algorithm": "ed25519",
                            "public_key_base64": base64.b64encode(public_bytes).decode(),
                            "fingerprint_sha256": hashlib.sha256(public_bytes).hexdigest(),
                            "status": "active",
                            "not_before": "2026-01-01T00:00:00Z",
                            "not_after": None,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.registry_path = self.root / "registry.json"
        self.registry_path.write_bytes(b'{"schema_version":"1.0"}\n')
        self.output_path = self.root / "registry.sig.json"

    def run_script(self, private_path: Path, *, output_path: Path | None = None):
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "sign_registry.py"),
                "--registry",
                str(self.registry_path),
                "--private-key",
                str(private_path),
                "--trust-store",
                str(self.trust_path),
                "--key-id",
                "test-key",
                "--output",
                str(output_path or self.output_path),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

    def test_signing_writes_only_detached_signature_and_no_private_output(self):
        result = self.run_script(self.private_path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        detached = json.loads(self.output_path.read_text(encoding="utf-8"))
        self.assertEqual(set(detached), {"key_id", "algorithm", "signature"})
        self.assertEqual(detached["key_id"], "test-key")
        self.assertEqual(detached["algorithm"], "ed25519")
        signature = base64.b64decode(detached["signature"], validate=True)
        self.private_key.public_key().verify(signature, self.registry_path.read_bytes())
        private_bytes = self.private_path.read_text(encoding="ascii").strip()
        self.assertNotIn(private_bytes, result.stderr)
        self.assertNotIn(private_bytes, result.stdout)

    def test_signing_fails_closed_on_missing_or_mismatched_private_key(self):
        missing = self.run_script(self.root / "missing.pem")
        self.assertNotEqual(missing.returncode, 0)
        self.assertFalse(self.output_path.exists())

        other = Ed25519PrivateKey.generate()
        mismatch_path = self.root / "mismatch.pem"
        mismatch_path.write_bytes(
            other.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        mismatch = self.run_script(mismatch_path)
        self.assertNotEqual(mismatch.returncode, 0)
        self.assertFalse(self.output_path.exists())

    def test_signing_never_overwrites_private_key_or_other_inputs(self):
        cases = [self.private_path, self.registry_path, self.trust_path]
        originals = {path: path.read_bytes() for path in cases}
        for output_path in cases:
            with self.subTest(output_path=output_path.name):
                result = self.run_script(self.private_path, output_path=output_path)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(output_path.read_bytes(), originals[output_path])


if __name__ == "__main__":
    unittest.main()
