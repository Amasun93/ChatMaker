from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
RFC8032_PUBLIC_KEY = bytes.fromhex(
    "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
)
RFC8032_EMPTY_SIGNATURE = bytes.fromhex(
    "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155"
    "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"
)
MANIFEST = b'{"schema_version":1,"version":"0.1.0-test"}\n'
MANIFEST_SIGNATURE = (
    "SyJ5boc7K7eHH8zw3mkva+q/Zly36cmkXBb4sEdQvDMbWyF4mx/tcP0+/g5A+pdq"
    "YxFFGYbsGfRr4JYfp0yHBA=="
)


def load_verifier():
    path = ROOT / "scripts" / "core_release_signature.py"
    spec = importlib.util.spec_from_file_location("chatmaker_core_release_signature", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


class CoreReleaseSignatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.verifier = load_verifier()

    def detached(self, **changes: str) -> bytes:
        value = {
            "algorithm": "ed25519",
            "key_id": "chatmaker-official-2026-01",
            "signature": MANIFEST_SIGNATURE,
        }
        value.update(changes)
        return canonical_json(value)

    def patched_rfc_anchor(self):
        return mock.patch.multiple(
            self.verifier,
            OFFICIAL_PUBLIC_KEY=RFC8032_PUBLIC_KEY,
            OFFICIAL_PUBLIC_KEY_FINGERPRINT=hashlib.sha256(RFC8032_PUBLIC_KEY).hexdigest(),
        )

    def test_embedded_anchor_matches_the_existing_official_repository_key(self):
        trust = json.loads(
            (ROOT / "runtime" / "chatmaker" / "trust" / "official_registry_keys.json").read_text(
                encoding="utf-8"
            )
        )
        anchor = trust["keys"][0]
        self.assertEqual(self.verifier.OFFICIAL_KEY_ID, anchor["key_id"])
        self.assertEqual(
            self.verifier.OFFICIAL_PUBLIC_KEY,
            base64.b64decode(anchor["public_key_base64"], validate=True),
        )
        self.assertEqual(
            self.verifier.OFFICIAL_PUBLIC_KEY_FINGERPRINT,
            anchor["fingerprint_sha256"],
        )

    def test_rfc8032_test_vector_one_verifies(self):
        self.assertTrue(
            self.verifier.verify_ed25519(
                RFC8032_PUBLIC_KEY, b"", RFC8032_EMPTY_SIGNATURE
            )
        )

    def test_rejects_wrong_lengths_types_and_zero_values(self):
        cases = (
            (RFC8032_PUBLIC_KEY[:-1], b"", RFC8032_EMPTY_SIGNATURE),
            (RFC8032_PUBLIC_KEY, b"", RFC8032_EMPTY_SIGNATURE[:-1]),
            (b"\0" * 32, b"", RFC8032_EMPTY_SIGNATURE),
            (RFC8032_PUBLIC_KEY, b"", b"\0" * 64),
            (bytearray(RFC8032_PUBLIC_KEY), b"", RFC8032_EMPTY_SIGNATURE),
            (RFC8032_PUBLIC_KEY, "", RFC8032_EMPTY_SIGNATURE),
        )
        for public_key, message, signature in cases:
            with self.subTest(key_length=len(public_key), signature_length=len(signature)):
                self.assertFalse(
                    self.verifier.verify_ed25519(public_key, message, signature)
                )

    def test_rejects_scalar_at_or_above_group_order_and_changed_scalar(self):
        group_order = self.verifier._L
        for scalar in (group_order, group_order + 1, 2**256 - 1):
            signature = RFC8032_EMPTY_SIGNATURE[:32] + scalar.to_bytes(32, "little")
            with self.subTest(scalar=scalar):
                self.assertFalse(
                    self.verifier.verify_ed25519(RFC8032_PUBLIC_KEY, b"", signature)
                )
        changed = bytearray(RFC8032_EMPTY_SIGNATURE)
        changed[-1] ^= 1
        self.assertFalse(
            self.verifier.verify_ed25519(RFC8032_PUBLIC_KEY, b"", bytes(changed))
        )

    def test_rejects_noncanonical_public_key_and_r_encoding(self):
        noncanonical = self.verifier._P.to_bytes(32, "little")
        self.assertFalse(
            self.verifier.verify_ed25519(
                noncanonical, b"", RFC8032_EMPTY_SIGNATURE
            )
        )
        signature = noncanonical + RFC8032_EMPTY_SIGNATURE[32:]
        self.assertFalse(
            self.verifier.verify_ed25519(RFC8032_PUBLIC_KEY, b"", signature)
        )

    def test_rejects_small_order_public_key_and_r_encoding(self):
        identity = b"\x01" + b"\0" * 31
        self.assertFalse(
            self.verifier.verify_ed25519(identity, b"", RFC8032_EMPTY_SIGNATURE)
        )
        signature = identity + RFC8032_EMPTY_SIGNATURE[32:]
        self.assertFalse(
            self.verifier.verify_ed25519(RFC8032_PUBLIC_KEY, b"", signature)
        )

    def test_rejects_changed_message_r_and_public_key(self):
        changed_r = bytearray(RFC8032_EMPTY_SIGNATURE)
        changed_r[0] ^= 1
        changed_key = bytearray(RFC8032_PUBLIC_KEY)
        changed_key[0] ^= 1
        self.assertFalse(
            self.verifier.verify_ed25519(
                RFC8032_PUBLIC_KEY, b"changed", RFC8032_EMPTY_SIGNATURE
            )
        )
        self.assertFalse(
            self.verifier.verify_ed25519(
                RFC8032_PUBLIC_KEY, b"", bytes(changed_r)
            )
        )
        self.assertFalse(
            self.verifier.verify_ed25519(
                bytes(changed_key), b"", RFC8032_EMPTY_SIGNATURE
            )
        )

    def test_domain_separated_canonical_manifest_verifies(self):
        with self.patched_rfc_anchor():
            result = self.verifier.verify_release_manifest(
                MANIFEST, self.detached()
            )
        self.assertEqual(result["algorithm"], "ed25519")
        self.assertEqual(result["key_id"], "chatmaker-official-2026-01")

    def test_wrong_domain_fails_closed(self):
        with self.patched_rfc_anchor(), mock.patch.object(
            self.verifier, "DOMAIN_SEPARATOR", b"Wrong domain\0"
        ):
            with self.assertRaises(self.verifier.ReleaseSignatureError):
                self.verifier.verify_release_manifest(MANIFEST, self.detached())

    def test_wrong_algorithm_key_id_and_fingerprint_fail_closed(self):
        with self.patched_rfc_anchor():
            for detached in (
                self.detached(algorithm="Ed25519"),
                self.detached(key_id="unknown-key"),
            ):
                with self.subTest(detached=detached):
                    with self.assertRaises(self.verifier.ReleaseSignatureError):
                        self.verifier.verify_release_manifest(MANIFEST, detached)
        with self.patched_rfc_anchor(), mock.patch.object(
            self.verifier, "OFFICIAL_PUBLIC_KEY_FINGERPRINT", "0" * 64
        ):
            with self.assertRaises(self.verifier.ReleaseSignatureError):
                self.verifier.verify_release_manifest(MANIFEST, self.detached())

    def test_duplicate_or_noncanonical_json_fails_closed(self):
        duplicate_manifest = b'{"schema_version":1,"schema_version":1,"version":"0.1.0-test"}\n'
        duplicate_detached = (
            b'{"algorithm":"ed25519","algorithm":"ed25519",'
            b'"key_id":"chatmaker-official-2026-01","signature":"'
            + MANIFEST_SIGNATURE.encode("ascii")
            + b'"}\n'
        )
        noncanonical_manifest = b'{"version": "0.1.0-test", "schema_version": 1}\n'
        with self.patched_rfc_anchor():
            for manifest, detached in (
                (duplicate_manifest, self.detached()),
                (MANIFEST, duplicate_detached),
                (noncanonical_manifest, self.detached()),
                (MANIFEST, self.detached() + b"\n"),
            ):
                with self.subTest(manifest=manifest, detached=detached):
                    with self.assertRaises(self.verifier.ReleaseSignatureError):
                        self.verifier.verify_release_manifest(manifest, detached)

    def test_noncanonical_base64_fails_closed(self):
        with self.patched_rfc_anchor():
            for signature in (
                MANIFEST_SIGNATURE.rstrip("="),
                MANIFEST_SIGNATURE + "=",
                MANIFEST_SIGNATURE.replace("+", "-"),
                MANIFEST_SIGNATURE + "\n",
            ):
                with self.subTest(signature=signature):
                    with self.assertRaises(self.verifier.ReleaseSignatureError):
                        self.verifier.verify_release_manifest(
                            MANIFEST, self.detached(signature=signature)
                        )

    def test_matches_cryptography_for_rfc_vector_and_tampering_when_available(self):
        try:
            from cryptography.exceptions import InvalidSignature
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        except ImportError:
            self.skipTest("cryptography is not installed")
        key = Ed25519PublicKey.from_public_bytes(RFC8032_PUBLIC_KEY)
        key.verify(RFC8032_EMPTY_SIGNATURE, b"")
        corrupted = bytes([RFC8032_EMPTY_SIGNATURE[0] ^ 1]) + RFC8032_EMPTY_SIGNATURE[1:]
        with self.assertRaises(InvalidSignature):
            key.verify(corrupted, b"")
        self.assertFalse(
            self.verifier.verify_ed25519(RFC8032_PUBLIC_KEY, b"", corrupted)
        )


if __name__ == "__main__":
    unittest.main()
