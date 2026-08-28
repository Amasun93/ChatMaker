from __future__ import annotations

import importlib.util
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile
import os
import subprocess

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[2]


def load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CoreRuntimeContractTests(unittest.TestCase):
    def test_bootstrap_ignores_optional_dependency_data_scripts(self):
        """Keeps fontTools utilities out while accepting its runtime library wheel."""
        bootstrap = load_script("bootstrap.py")
        with tempfile.TemporaryDirectory() as temporary:
            wheel = Path(temporary) / "fonttools-1.0-py3-none-any.whl"
            payloads = {
                "fontTools/__init__.py": b"",
                "fonttools-1.0.data/scripts/ttx": b"#!/usr/bin/python\n",
                "fonttools-1.0.data/data/share/man/man1/ttx.1": b"manual\n",
                "fonttools-1.0.dist-info/METADATA": b"Metadata-Version: 2.1\nName: fonttools\nVersion: 1.0\n",
                "fonttools-1.0.dist-info/WHEEL": b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
            }
            rows = []
            for name, value in sorted(payloads.items()):
                encoded = base64.urlsafe_b64encode(hashlib.sha256(value).digest()).rstrip(b"=").decode("ascii")
                rows.append([name, f"sha256={encoded}", str(len(value))])
            record_name = "fonttools-1.0.dist-info/RECORD"
            rows.append([record_name, "", ""])
            record = io.StringIO(newline="")
            csv.writer(record, lineterminator="\n").writerows(rows)
            with zipfile.ZipFile(wheel, "w") as archive:
                for name, value in payloads.items():
                    archive.writestr(name, value)
                archive.writestr(record_name, record.getvalue())

            expected, _ = bootstrap._wheel_contract(wheel)

        self.assertIn("fontTools/__init__.py", expected)
        self.assertNotIn("fonttools-1.0.data/scripts/ttx", expected)
        self.assertNotIn("fonttools-1.0.data/data/share/man/man1/ttx.1", expected)

    def test_marker_environment_defines_empty_extra_for_wheel_metadata(self):
        """Catches fontTools-style optional extras crashing release validation."""
        prepare = load_script("prepare_core_runtime.py")
        self.assertEqual(prepare._marker_environment("windows-amd64")["extra"], "")

    def test_lock_contains_the_metadata_required_typing_extensions_for_python_311_and_312(self):
        """Catches omitting referencing's Python <3.13 transitive dependency."""
        lines = (ROOT / "distribution" / "core-runtime" / "requirements.lock").read_text(encoding="utf-8").splitlines()
        self.assertIn("typing-extensions==4.15.0", lines)

    def test_prepared_runtime_manifest_rejects_a_wheel_not_named_in_the_lock(self):
        """Catches a release wheelhouse gaining an unhashed executable wheel."""
        prepare = load_script("prepare_core_runtime.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            wheelhouse = root / "wheelhouse"
            wheelhouse.mkdir()
            (wheelhouse / "unexpected-1.0-py3-none-any.whl").write_bytes(b"not a wheel")
            lock = root / "requirements.lock"
            lock.write_text("expected==1.0\n", encoding="utf-8")

            with self.assertRaises(prepare.PreparationError):
                prepare.prepare_manifest(
                    wheelhouse=wheelhouse,
                    lock_path=lock,
                    platform_tag="windows-amd64",
                    core_wheel="chatmaker-0.1.0-py3-none-any.whl",
                )

    def test_release_builder_requires_a_manifest_bound_prepared_platform_bundle(self):
        """Catches returning to a source-only Core ZIP with no offline runtime inputs."""
        builder = load_script("build_release.py")
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(builder.ReleaseError):
                builder.build_release(
                    ROOT,
                    Path(temporary),
                    "0.1.0-rc5",
                    platform_tag="windows-amd64",
                    prepared_root=Path(temporary) / "missing",
                )

    def test_release_zip_metadata_is_platform_independent(self):
        """Catches ZipInfo defaults leaking the build host into central-directory records."""
        builder = load_script("build_release.py")
        info = builder.release_zip_info("ChatMaker-Core-1.0.0-windows-amd64/README.md")
        self.assertEqual(info.create_system, 3)
        self.assertEqual(info.create_version, 20)
        self.assertEqual(info.extract_version, 20)
        self.assertEqual(info.flag_bits, 0)
        self.assertEqual(info.external_attr, 0o100644 << 16)

    def test_release_builder_emits_a_canonical_manifest_binding_every_release_identity(self):
        """Catches publishing an archive whose detached signature cannot bind its executable identity."""
        builder = load_script("build_release.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepared = root / "prepared"
            wheelhouse = prepared / "wheelhouse"
            wheelhouse.mkdir(parents=True)
            wheel = wheelhouse / "chatmaker-0.1.0rc5-py3-none-any.whl"
            payloads = {
                "chatmaker/__init__.py": b"",
                "chatmaker-0.1.0rc5.dist-info/METADATA": b"Metadata-Version: 2.1\nName: chatmaker\nVersion: 0.1.0rc5\n",
                "chatmaker-0.1.0rc5.dist-info/WHEEL": b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
            }
            rows: list[list[str]] = []
            for name, value in sorted(payloads.items()):
                encoded = base64.urlsafe_b64encode(hashlib.sha256(value).digest()).rstrip(b"=").decode("ascii")
                rows.append([name, f"sha256={encoded}", str(len(value))])
            rows.append(["chatmaker-0.1.0rc5.dist-info/RECORD", "", ""])
            record = io.StringIO(newline="")
            csv.writer(record, lineterminator="\n").writerows(rows)
            with zipfile.ZipFile(wheel, "w") as archive:
                for name, value in payloads.items():
                    archive.writestr(name, value)
                archive.writestr("chatmaker-0.1.0rc5.dist-info/RECORD", record.getvalue())
            digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
            runtime_manifest = {
                "schema_version": 2,
                "platform_tag": "windows-amd64",
                "python_requires": "==3.11.*",
                "core_wheel": wheel.name,
                "wheels": [{"filename": wheel.name, "project": "chatmaker", "version": "0.1.0rc5", "size": wheel.stat().st_size, "sha256": digest, "tags": ["py3-none-any"], "requires": []}],
            }
            runtime_bytes = (json.dumps(runtime_manifest, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
            (prepared / "manifest.json").write_bytes(runtime_bytes)
            (prepared / "requirements.txt").write_bytes(f"chatmaker==0.1.0rc5 --hash=sha256:{digest}\n".encode("ascii"))

            result = builder.build_release(
                ROOT,
                root / "dist",
                "0.1.0-rc5",
                platform_tag="windows-amd64",
                prepared_root=prepared,
                release_sequence=17,
            )

            manifest_path = Path(result["release_manifest"])
            raw = manifest_path.read_bytes()
            manifest = json.loads(raw)
            self.assertEqual(raw, builder.canonical_json(manifest))
            self.assertEqual(manifest["release_sequence"], 17)
            self.assertEqual(manifest["core_version"], "0.1.0-rc5")
            self.assertEqual(manifest["core_wheel_version"], "0.1.0rc5")
            self.assertEqual(manifest["platform_tag"], "windows-amd64")
            self.assertEqual(manifest["python_tag"], "cp311")
            self.assertEqual(manifest["archive"]["filename"], Path(result["archive"]).name)
            self.assertEqual(manifest["archive"]["size"], Path(result["archive"]).stat().st_size)
            self.assertEqual(manifest["archive"]["sha256"], result["sha256"])
            self.assertEqual(manifest["runtime_manifest_sha256"], hashlib.sha256(runtime_bytes).hexdigest())

    def test_release_signer_uses_an_ephemeral_ed25519_key_and_rejects_a_wrong_anchor(self):
        """Catches accepting a private key that is unrelated to the embedded official trust anchor."""
        signer = load_script("sign_core_release.py")
        verifier = load_script("core_release_signature.py")
        key = Ed25519PrivateKey.generate()
        public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "release.manifest.json"
            manifest.write_bytes(b'{"schema_version":1,"version":"test"}\n')
            private_key = root / "test-private.pem"
            private_key.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))

            with mock.patch.multiple(
                signer,
                OFFICIAL_PUBLIC_KEY=public,
                OFFICIAL_PUBLIC_KEY_FINGERPRINT=hashlib.sha256(public).hexdigest(),
            ), mock.patch.multiple(
                verifier,
                OFFICIAL_PUBLIC_KEY=public,
                OFFICIAL_PUBLIC_KEY_FINGERPRINT=hashlib.sha256(public).hexdigest(),
            ):
                signed = signer.sign_manifest(manifest, private_key)
                verifier.verify_release_manifest(manifest.read_bytes(), Path(signed["signature_file"]).read_bytes())

            with self.assertRaises(signer.SigningError):
                signer.sign_manifest(manifest, private_key)

    def test_prepared_runtime_rejects_a_wheel_with_the_wrong_platform_tag(self):
        """Catches a prepared Windows bundle carrying a macOS-only executable wheel."""
        prepare = load_script("prepare_core_runtime.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            wheelhouse = root / "wheelhouse"
            wheelhouse.mkdir()
            wheel = wheelhouse / "chatmaker-1.0-cp311-cp311-macosx_11_0_arm64.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr("chatmaker/__init__.py", "")
                archive.writestr("chatmaker-1.0.dist-info/METADATA", "Metadata-Version: 2.1\nName: chatmaker\nVersion: 1.0\n")
                archive.writestr("chatmaker-1.0.dist-info/WHEEL", "Wheel-Version: 1.0\nRoot-Is-Purelib: false\nTag: cp311-cp311-macosx_11_0_arm64\n")
                archive.writestr("chatmaker-1.0.dist-info/RECORD", "")
            dependency = wheelhouse / "dummy-1.0-py3-none-any.whl"
            with zipfile.ZipFile(dependency, "w") as archive:
                archive.writestr("dummy/__init__.py", "")
                archive.writestr("dummy-1.0.dist-info/METADATA", "Metadata-Version: 2.1\nName: dummy\nVersion: 1.0\n")
                archive.writestr("dummy-1.0.dist-info/WHEEL", "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
                archive.writestr("dummy-1.0.dist-info/RECORD", "")
            lock = root / "requirements.lock"
            lock.write_text("dummy==1.0\n", encoding="utf-8")

            with self.assertRaises(prepare.PreparationError):
                prepare.prepare_manifest(
                    wheelhouse=wheelhouse,
                    lock_path=lock,
                    platform_tag="windows-amd64",
                    core_wheel=wheel.name,
                )

    def test_prepared_runtime_rejects_a_lock_that_is_not_the_wheel_dependency_closure(self):
        """Catches a pinned but unrelated wheel replacing a dependency required by signed wheel metadata."""
        prepare = load_script("prepare_core_runtime.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            wheelhouse = root / "wheelhouse"
            wheelhouse.mkdir()
            def write_wheel(path: Path, payloads: dict[str, bytes], record_name: str) -> None:
                rows: list[list[str]] = []
                for name, value in sorted(payloads.items()):
                    encoded = base64.urlsafe_b64encode(hashlib.sha256(value).digest()).rstrip(b"=").decode("ascii")
                    rows.append([name, f"sha256={encoded}", str(len(value))])
                rows.append([record_name, "", ""])
                record = io.StringIO(newline="")
                csv.writer(record, lineterminator="\n").writerows(rows)
                with zipfile.ZipFile(path, "w") as archive:
                    for name, value in payloads.items():
                        archive.writestr(name, value)
                    archive.writestr(record_name, record.getvalue())
            core = wheelhouse / "chatmaker-1.0-py3-none-any.whl"
            write_wheel(core, {
                "chatmaker/__init__.py": b"",
                "chatmaker-1.0.dist-info/METADATA": b"Metadata-Version: 2.1\nName: chatmaker\nVersion: 1.0\nRequires-Dist: required-dependency>=2\n",
                "chatmaker-1.0.dist-info/WHEEL": b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
            }, "chatmaker-1.0.dist-info/RECORD")
            unrelated = wheelhouse / "unrelated-2.0-py3-none-any.whl"
            write_wheel(unrelated, {
                "unrelated/__init__.py": b"",
                "unrelated-2.0.dist-info/METADATA": b"Metadata-Version: 2.1\nName: unrelated\nVersion: 2.0\n",
                "unrelated-2.0.dist-info/WHEEL": b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
            }, "unrelated-2.0.dist-info/RECORD")
            lock = root / "requirements.lock"
            lock.write_text("unrelated==2.0\n", encoding="utf-8")

            with self.assertRaises(prepare.PreparationError):
                prepare.prepare_manifest(
                    wheelhouse=wheelhouse,
                    lock_path=lock,
                    platform_tag="windows-amd64",
                    core_wheel=core.name,
                )

    def test_release_version_rejects_portable_aliases_and_must_match_the_core_wheel(self):
        """Catches reserved/trailing/Unicode aliases and a release label disagreeing with Core metadata."""
        builder = load_script("build_release.py")
        for version in ("CON", "1.0. ", "e\u0301"):
            with self.subTest(version=version), self.assertRaisesRegex(builder.ReleaseError, "release_version_invalid"):
                builder.build_release(ROOT, Path(tempfile.gettempdir()) / "unused", version, platform_tag="windows-amd64", prepared_root=Path("missing"))

    def test_core_source_tree_rejects_a_real_link_or_windows_junction(self):
        """Catches release enumeration traversing a reparse-backed source directory outside its root."""
        builder = load_script("build_release.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / "outside"
            outside.mkdir()
            (outside / "payload.txt").write_text("outside", encoding="utf-8")
            source = root / "payload"
            if os.name == "nt":
                created = subprocess.run(["cmd", "/d", "/c", "mklink", "/J", str(source), str(outside)], text=True, capture_output=True)
                if created.returncode:
                    self.skipTest("Windows junction creation unavailable")
            else:
                source.symlink_to(outside, target_is_directory=True)
            try:
                with mock.patch.object(builder, "CORE_PATHS", ("payload",)), self.assertRaises(builder.ReleaseError):
                    builder._core_files(root)
            finally:
                if os.path.lexists(source):
                    source.rmdir() if source.is_dir() else source.unlink()


if __name__ == "__main__":
    unittest.main()
