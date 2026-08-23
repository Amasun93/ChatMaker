from __future__ import annotations

import hashlib
import base64
import csv
import io
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile
import runpy

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = ROOT / "scripts" / "bootstrap.py"


def _symlink_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name)
    info.create_system = 3
    info.external_attr = (0o120777 << 16)
    return info


def _platform_tag() -> str:
    return "windows-amd64" if os.name == "nt" else "macos-arm64" if platform.machine().lower() in {"arm64", "aarch64"} else "macos-x86_64"


def _wheel(path: Path, *, project: str, version: str, files: dict[str, str]) -> None:
    dist = f"{project.replace('-', '_')}-{version}.dist-info"
    payloads = {name: value.encode("utf-8") for name, value in files.items()}
    payloads[f"{dist}/METADATA"] = f"Metadata-Version: 2.1\nName: {project}\nVersion: {version}\n".encode("utf-8")
    payloads[f"{dist}/WHEEL"] = b"Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
    rows: list[list[str]] = []
    for name, value in sorted(payloads.items()):
        digest = base64.urlsafe_b64encode(hashlib.sha256(value).digest()).rstrip(b"=").decode("ascii")
        rows.append([name, f"sha256={digest}", str(len(value))])
    rows.append([f"{dist}/RECORD", "", ""])
    record = io.StringIO(newline="")
    csv.writer(record, lineterminator="\n").writerows(rows)
    with zipfile.ZipFile(path, "w") as archive:
        for name, value in payloads.items():
            archive.writestr(name, value)
        archive.writestr(f"{dist}/RECORD", record.getvalue())


class BootstrapTests(unittest.TestCase):
    """End-to-end contracts for the stdlib-only Core bootstrapper."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._trusted_scripts = tempfile.TemporaryDirectory(prefix="chatmaker-trusted-bootstrap-")
        cls.private_key = Ed25519PrivateKey.generate()
        public = cls.private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        destination = Path(cls._trusted_scripts.name)
        shutil.copy2(BOOTSTRAP, destination / "bootstrap.py")
        verifier = (ROOT / "scripts" / "core_release_signature.py").read_text(encoding="utf-8")
        verifier = verifier.replace(
            "89b25c42329e5deff966621a115f479883b78fd3db5610f34a5600f4e8fd1da9",
            public.hex(),
        ).replace(
            "70570b179cf452abcc7486f76a408a25faee3702433663e99b7418498d725f67",
            hashlib.sha256(public).hexdigest(),
        )
        (destination / "core_release_signature.py").write_text(verifier, encoding="utf-8", newline="\n")
        cls.trusted_bootstrap = destination / "bootstrap.py"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._trusted_scripts.cleanup()

    @staticmethod
    def _canonical_json(value: object) -> bytes:
        return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")

    def _release_evidence(
        self,
        archive: Path,
        version: str,
        *,
        wheel_version: str | None = None,
        runtime_manifest_sha256: str | None = None,
        release_sequence: int = 10,
        platform_tag: str | None = None,
    ) -> tuple[Path, Path]:
        manifest = {
            "schema_version": 1,
            "release_sequence": release_sequence,
            "core_version": version,
            "core_wheel_version": version if wheel_version is None else wheel_version,
            "platform_tag": _platform_tag() if platform_tag is None else platform_tag,
            "python_tag": "cp311",
            "archive": {
                "filename": archive.name,
                "size": archive.stat().st_size,
                "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            },
            "runtime_manifest_sha256": "0" * 64 if runtime_manifest_sha256 is None else runtime_manifest_sha256,
            "release_metadata": {
                "archive_format": "zip",
                "compression": "deflate-9",
                "member_count": len(zipfile.ZipFile(archive).infolist()),
                "timestamp": "2026-08-14T00:00:00Z",
            },
        }
        manifest_path = archive.with_suffix(archive.suffix + ".manifest.json")
        manifest_bytes = self._canonical_json(manifest)
        manifest_path.write_bytes(manifest_bytes)
        signature = self.private_key.sign(b"ChatMaker Core Release Manifest v1\0" + manifest_bytes)
        signature_path = archive.with_suffix(archive.suffix + ".manifest.sig.json")
        signature_path.write_bytes(self._canonical_json({
            "algorithm": "ed25519",
            "key_id": "chatmaker-official-2026-01",
            "signature": base64.b64encode(signature).decode("ascii"),
        }))
        return manifest_path, signature_path

    def _make_core(self, directory: Path, version: str = "9.8.7", *, fail_auto: bool = False, release_sequence: int = 10) -> tuple[Path, Path, Path, Path]:
        """Build a tiny, real installable Core archive with a local console entry point."""
        tag = _platform_tag()
        root = directory / f"ChatMaker-Core-{version}-{tag}"
        package = root / "runtime" / "chatmaker"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "installer.py").write_text("", encoding="utf-8")
        (root / "pyproject.toml").write_text(f"[project]\nname='chatmaker'\nversion='{version}'\n", encoding="utf-8")
        scripts = root / "scripts"
        scripts.mkdir()
        (scripts / "bootstrap.py").write_bytes(BOOTSTRAP.read_bytes())
        (scripts / "core_release_signature.py").write_bytes((ROOT / "scripts" / "core_release_signature.py").read_bytes())
        runtime = root / "core-runtime"
        wheelhouse = runtime / "wheelhouse"
        wheelhouse.mkdir(parents=True)
        wheel_name = f"chatmaker-{version}-py3-none-any.whl"
        auto = (
            "import json, os, sys\nfrom pathlib import Path\n"
            "def main():\n"
            " home=Path(os.environ['HOME']); (home/'auto.log').parent.mkdir(parents=True,exist_ok=True); (home/'auto.log').open('a',encoding='utf-8').write('auto\\n'); (home/'argv.log').open('a',encoding='utf-8').write(' '.join(sys.argv[1:])+'\\n'); (home/'env.log').write_text('|'.join(os.environ.get(k,'') for k in ('CODEX_HOME','WORKBUDDY_HOME','CHATMAKER_SKILL_ROOT','PIP_INDEX_URL')),encoding='utf-8')\n"
            + (" print(json.dumps({'success':False,'status':'failed'})); return 2\n" if fail_auto else " print(json.dumps({'success':True,'status':'ready_with_limits'})); return 0\n")
            + "\nif __name__ == '__main__': raise SystemExit(main())\n"
        )
        _wheel(wheelhouse / wheel_name, project="chatmaker", version=version, files={"chatmaker/__init__.py": "", "chatmaker/installers/__init__.py": "", "chatmaker/installers/auto.py": auto})
        digest = hashlib.sha256((wheelhouse / wheel_name).read_bytes()).hexdigest()
        manifest = {"schema_version": 2, "platform_tag": tag, "python_requires": "==3.11.*", "core_wheel": wheel_name, "wheels": [{"filename": wheel_name, "project": "chatmaker", "version": version, "size": (wheelhouse / wheel_name).stat().st_size, "sha256": digest, "tags": ["py3-none-any"], "requires": []}]}
        (runtime / "manifest.json").write_bytes((json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii"))
        (runtime / "requirements.txt").write_bytes(f"chatmaker=={version} --hash=sha256:{digest}\n".encode("ascii"))
        archive = directory / f"ChatMaker-Core-{version}.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    bundle.write(path, path.relative_to(directory).as_posix())
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        checksum = directory / f"{archive.name}.sha256"
        checksum.write_text(f"{digest}  {archive.name}\n", encoding="ascii")
        manifest_path, signature_path = self._release_evidence(
            archive,
            version,
            runtime_manifest_sha256=hashlib.sha256((runtime / "manifest.json").read_bytes()).hexdigest(),
            release_sequence=release_sequence,
        )
        return archive, checksum, manifest_path, signature_path

    def _run(self, archive: Path, checksum: Path, manifest: Path, signature: Path, home: Path, *, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(self.trusted_bootstrap),
                "--archive",
                str(archive),
                "--checksum",
                str(checksum),
                "--release-manifest",
                str(manifest),
                "--release-signature",
                str(signature),
                "--home",
                str(home),
            ],
            cwd=Path(tempfile.gettempdir()),
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=180,
        )

    def test_bootstrap_cli_reports_invalid_arguments_as_json(self):
        """Catches argparse prose escaping a machine-readable bootstrap failure boundary."""
        result = subprocess.run(
            [sys.executable, str(BOOTSTRAP)],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["success"])
        self.assertEqual(report["status"], "failed")

    def test_bootstrap_installs_a_checked_local_core_in_a_unicode_home_and_reuses_it(self):
        """Catches bootstrap rebuilding an existing verified venv or skipping auto convergence."""
        with tempfile.TemporaryDirectory(prefix="chatmaker bootstrap ") as temporary:
            base = Path(temporary)
            archive, checksum, manifest, signature = self._make_core(base)
            home = base / "老师 的 ChatMaker 家目录"
            auto_log = home / "auto.log"
            environment = os.environ.copy()
            environment.update(
                {
                    "HOME": str(home),
                    "USERPROFILE": str(home),
                    "PIP_NO_INDEX": "1",
                    "PIP_INDEX_URL": "http://127.0.0.1:1/forbidden",
                    "PIP_EXTRA_INDEX_URL": "http://127.0.0.1:1/also-forbidden",
                    "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                    "PYTHONIOENCODING": "cp1252",
                    "CODEX_HOME": str(base / "wrong-codex"),
                    "WORKBUDDY_HOME": str(base / "wrong-workbuddy"),
                    "CHATMAKER_SKILL_ROOT": str(base / "wrong-skills"),
                }
            )

            first = self._run(archive, checksum, manifest, signature, home, env=environment)
            self.assertEqual(first.returncode, 0, first.stderr)
            installed = json.loads(first.stdout)
            self.assertTrue(installed["success"])
            self.assertEqual(installed["status"], "installed")
            venv = home / ".chatmaker" / "versions" / "9.8.7" / "venv"
            self.assertEqual(Path(installed["venv"]), venv)
            self.assertTrue(venv.is_dir())
            self.assertFalse((home / ".chatmaker" / "versions" / "9.8.7" / ".venv-files.json").exists())
            launcher = Path(installed["launcher"])
            self.assertTrue(launcher.is_file())
            python = venv / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")
            imported = subprocess.run(
                [
                    str(python), "-B", "-c",
                    "import chatmaker,json; print(json.dumps(str(chatmaker.__file__)))",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(imported.returncode, 0, imported.stderr)
            self.assertTrue(Path(json.loads(imported.stdout)).resolve().is_relative_to(venv.resolve()))
            inherited = subprocess.run(
                [
                    str(python), "-I", "-S", "-B", "-c",
                    "import importlib.util,os,sys; from pathlib import Path; root=Path(sys.executable).parent.parent; site=root/('Lib/site-packages' if os.name=='nt' else f'lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages'); sys.path.insert(0,str(site)); raise SystemExit(0 if importlib.util.find_spec('cryptography') is None else 9)",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(inherited.returncode, 0, inherited.stderr)
            before = (home / ".chatmaker" / "versions" / "9.8.7" / ".bootstrap.json").read_bytes()

            second = self._run(archive, checksum, manifest, signature, home, env=environment)
            self.assertEqual(second.returncode, 0, second.stderr)
            repeated = json.loads(second.stdout)
            self.assertTrue(repeated["success"])
            self.assertEqual(repeated["status"], "already_current")
            self.assertEqual(before, (home / ".chatmaker" / "versions" / "9.8.7" / ".bootstrap.json").read_bytes())
            launcher_command = ["cmd", "/d", "/c", str(launcher), "doctor"] if os.name == "nt" else [str(launcher), "doctor"]
            launched = subprocess.run(launcher_command, env=environment, text=True, capture_output=True)
            self.assertEqual(launched.returncode, 0, launched.stderr)
            self.assertEqual(auto_log.read_text(encoding="utf-8"), "auto\nauto\nauto\n")
            self.assertEqual((home / "argv.log").read_text(encoding="utf-8").splitlines()[-1], f"doctor --home {home}")
            self.assertEqual((home / "env.log").read_text(encoding="utf-8"), "|||")
            self.assertFalse(any((base / name).exists() for name in ("wrong-codex", "wrong-workbuddy", "wrong-skills")))

    def test_bootstrap_rejects_a_bad_checksum_before_creating_its_install_root(self):
        """Catches unpacking or creating a version directory before archive identity is proven."""
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            archive, checksum, manifest, signature = self._make_core(base)
            checksum.write_text("0" * 64 + f"  {archive.name}\n", encoding="ascii")
            home = base / "home"
            result = self._run(archive, checksum, manifest, signature, home, env=os.environ.copy())

            self.assertNotEqual(result.returncode, 0)
            report = json.loads(result.stdout)
            self.assertFalse(report["success"])
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["error"], "BootstrapError")
            self.assertFalse((home / ".chatmaker" / "versions").exists())

    def test_bootstrap_rejects_a_tampered_detached_release_manifest_before_install(self):
        """Catches trusting archive metadata after the signed canonical manifest has changed."""
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            archive, checksum, manifest, signature = self._make_core(base)
            value = json.loads(manifest.read_bytes())
            value["release_sequence"] += 1
            manifest.write_bytes(self._canonical_json(value))
            home = base / "home"

            result = self._run(archive, checksum, manifest, signature, home, env=os.environ.copy())

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)["detail"], "release_signature_invalid")
            self.assertFalse((home / ".chatmaker").exists())

    def test_bootstrap_rejects_a_validly_signed_manifest_for_another_platform(self):
        """Catches a signed macOS release being accepted by the Windows bootstrap or vice versa."""
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            archive, checksum, _, _ = self._make_core(base)
            other = "macos-arm64" if _platform_tag() == "windows-amd64" else "windows-amd64"
            runtime = base / f"ChatMaker-Core-9.8.7-{_platform_tag()}" / "core-runtime" / "manifest.json"
            manifest, signature = self._release_evidence(
                archive,
                "9.8.7",
                runtime_manifest_sha256=hashlib.sha256(runtime.read_bytes()).hexdigest(),
                platform_tag=other,
            )
            home = base / "home"

            result = self._run(archive, checksum, manifest, signature, home, env=os.environ.copy())

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)["detail"], "release_manifest_invalid")
            self.assertFalse((home / ".chatmaker").exists())

    def test_bootstrap_rejects_a_signed_release_sequence_rollback(self):
        """Catches a valid older release replay replacing a newer active version."""
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            newer = self._make_core(base, "9.8.7", release_sequence=20)
            older = self._make_core(base, "9.8.8", release_sequence=19)
            home = base / "home"
            first = self._run(*newer, home, env=os.environ.copy())
            self.assertEqual(first.returncode, 0, first.stdout)
            active_before = (home / ".chatmaker" / "active.json").read_bytes()

            replayed = self._run(*older, home, env=os.environ.copy())

            self.assertNotEqual(replayed.returncode, 0)
            self.assertEqual(json.loads(replayed.stdout)["detail"], "release_sequence_rollback")
            self.assertEqual((home / ".chatmaker" / "active.json").read_bytes(), active_before)

    def test_bootstrap_rejects_unsafe_archive_members_without_extracting_them(self):
        """Catches a ZIP-slip member being written outside the staged Core tree."""
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            archive = base / "ChatMaker-Core-9.8.7.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("ChatMaker-Core-9.8.7/pyproject.toml", "[project]\nname='chatmaker'\nversion='9.8.7'\n")
                bundle.writestr("ChatMaker-Core-9.8.7/../outside.txt", "escape")
            checksum = base / f"{archive.name}.sha256"
            checksum.write_text(
                f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n",
                encoding="ascii",
            )
            manifest, signature = self._release_evidence(archive, "9.8.7")
            home = base / "home"
            result = self._run(archive, checksum, manifest, signature, home, env=os.environ.copy())

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)["error"], "BootstrapError")
            self.assertFalse((base / "outside.txt").exists())
            self.assertFalse((home / ".chatmaker" / "versions").exists())

    def test_bootstrap_rejects_link_and_file_directory_alias_members(self):
        """Catches archive metadata that could create links or collide with an extraction directory."""
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            for name, build in (
                (
                    "link",
                    lambda bundle: (
                        bundle.writestr("ChatMaker-Core-9.8.7/pyproject.toml", "[project]\nname='chatmaker'\nversion='9.8.7'\n"),
                        bundle.writestr("ChatMaker-Core-9.8.7/runtime/chatmaker/__init__.py", ""),
                        bundle.writestr(_symlink_info("ChatMaker-Core-9.8.7/runtime/escape"), "outside"),
                    ),
                ),
                (
                    "alias",
                    lambda bundle: (
                        bundle.writestr("ChatMaker-Core-9.8.7/pyproject.toml", "[project]\nname='chatmaker'\nversion='9.8.7'\n"),
                        bundle.writestr("ChatMaker-Core-9.8.7/runtime", "not a directory"),
                        bundle.writestr("ChatMaker-Core-9.8.7/runtime/chatmaker/__init__.py", ""),
                    ),
                ),
            ):
                archive = base / f"ChatMaker-Core-9.8.7-{name}.zip"
                with zipfile.ZipFile(archive, "w") as bundle:
                    build(bundle)
                checksum = base / f"{archive.name}.sha256"
                checksum.write_text(
                    f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n",
                    encoding="ascii",
                )
                manifest, signature = self._release_evidence(archive, "9.8.7")
                home = base / f"home-{name}"
                result = self._run(archive, checksum, manifest, signature, home, env=os.environ.copy())
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(json.loads(result.stdout)["error"], "BootstrapError")
                self.assertFalse((home / ".chatmaker" / "versions").exists())

    def test_bootstrap_rejects_portable_case_and_nfc_member_collisions(self):
        """Catches archives whose distinct names alias on Windows or normalization-aware filesystems."""
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = f"ChatMaker-Core-9.8.7-{_platform_tag()}"
            for label, names in (
                ("case", ("Payload.py", "payload.py")),
                ("nfc", ("caf\u00e9.py", "cafe\u0301.py")),
            ):
                archive = base / f"collision-{label}.zip"
                with zipfile.ZipFile(archive, "w") as bundle:
                    for name in names:
                        bundle.writestr(f"{root}/{name}", name)
                checksum = archive.with_suffix(".zip.sha256")
                checksum.write_text(f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n", encoding="ascii")
                manifest, signature = self._release_evidence(archive, "9.8.7")

                result = self._run(archive, checksum, manifest, signature, base / f"home-{label}", env=os.environ.copy())

                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(json.loads(result.stdout)["detail"], "archive_member_collision")

    def test_management_home_rejects_reserved_trailing_and_non_nfc_segments(self):
        """Catches Windows path aliases entering the managed versions/lock/active namespace."""
        bootstrap = runpy.run_path(str(BOOTSTRAP))
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            for name in ("CON", "alias. ", "cafe\u0301"):
                with self.subTest(name=name), self.assertRaisesRegex(bootstrap["BootstrapError"], "management_path_unsafe"):
                    bootstrap["_validate_management_aliases"](base / name)

    @unittest.skipUnless(os.name == "nt", "Windows junction contract")
    def test_bootstrap_rejects_a_real_windows_junction_in_the_management_root(self):
        """Catches a home management path being redirected through an NTFS reparse point."""
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            archive, checksum, manifest, signature = self._make_core(base)
            outside = base / "outside-home"
            outside.mkdir()
            selected_home = base / "junction-home"
            created = subprocess.run(["cmd", "/d", "/c", "mklink", "/J", str(selected_home), str(outside)], text=True, capture_output=True)
            if created.returncode:
                self.skipTest("Windows junction creation unavailable")
            try:
                result = self._run(archive, checksum, manifest, signature, selected_home, env=os.environ.copy())
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(json.loads(result.stdout)["detail"], "management_path_unsafe")
                self.assertFalse((outside / ".chatmaker").exists())
            finally:
                if os.path.lexists(selected_home):
                    selected_home.rmdir()

    def test_failed_new_version_leaves_the_previous_active_launcher_unchanged(self):
        """Catches a failed auto convergence switching the active user launcher too early."""
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            first_archive, first_checksum, first_manifest, first_signature = self._make_core(base, "9.8.7", release_sequence=10)
            second_archive, second_checksum, second_manifest, second_signature = self._make_core(base, "9.8.8", fail_auto=True, release_sequence=11)
            home = base / "home"
            environment = os.environ.copy()
            environment.update({"HOME": str(home), "USERPROFILE": str(home), "PIP_NO_INDEX": "1"})

            first = self._run(first_archive, first_checksum, first_manifest, first_signature, home, env=environment)
            self.assertEqual(first.returncode, 0, first.stdout)
            active = home / ".chatmaker" / "active.json"
            launcher = Path(json.loads(first.stdout)["launcher"])
            active_before = active.read_bytes()
            launcher_before = launcher.read_bytes()

            failed = self._run(second_archive, second_checksum, second_manifest, second_signature, home, env=environment)

            self.assertNotEqual(failed.returncode, 0)
            self.assertFalse(json.loads(failed.stdout)["success"])
            self.assertEqual(active.read_bytes(), active_before)
            self.assertEqual(launcher.read_bytes(), launcher_before)

    def test_concurrent_bootstraps_are_serialized_by_one_cross_process_home_lock(self):
        """Catches two installers interleaving version creation and the single active pointer switch."""
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            archive, checksum, manifest, signature = self._make_core(base)
            home = base / "home"
            command = [
                sys.executable,
                str(self.trusted_bootstrap),
                "--archive", str(archive),
                "--checksum", str(checksum),
                "--release-manifest", str(manifest),
                "--release-signature", str(signature),
                "--home", str(home),
            ]
            environment = {**os.environ, "PIP_INDEX_URL": "http://127.0.0.1:1/forbidden"}
            processes = [
                subprocess.Popen(command, cwd=tempfile.gettempdir(), env=environment, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                for _ in range(2)
            ]
            completed = [process.communicate(timeout=240) + (process.returncode,) for process in processes]

            self.assertTrue(all(returncode == 0 for _, _, returncode in completed), completed)
            reports = [json.loads(stdout) for stdout, _, _ in completed]
            self.assertEqual({report["status"] for report in reports}, {"installed", "already_current"})
            active = home / ".chatmaker" / "active.json"
            raw = active.read_bytes()
            self.assertEqual(raw, self._canonical_json(json.loads(raw)))
            self.assertEqual(json.loads(raw)["version"], "9.8.7")

    def test_active_pointer_fault_boundaries_leave_one_complete_recoverable_value(self):
        """Catches torn or absent active state at file-fsync, replace, and parent-fsync crash boundaries."""
        bootstrap = runpy.run_path(str(BOOTSTRAP))
        old = {
            "schema_version": 2,
            "version": "1.0.0",
            "archive_sha256": "1" * 64,
            "platform_tag": _platform_tag(),
            "release_sequence": 1,
            "release_manifest_sha256": "2" * 64,
        }
        new = {**old, "version": "2.0.0", "archive_sha256": "3" * 64, "release_sequence": 2, "release_manifest_sha256": "4" * 64}
        for boundary, expected in (
            ("after_active_file_fsync", old),
            ("after_active_replace", new),
            ("after_active_parent_fsync", new),
        ):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as temporary:
                active = Path(temporary) / "active.json"
                active.write_bytes(self._canonical_json(old))

                def fail_here(name: str) -> None:
                    if name == boundary:
                        raise RuntimeError(boundary)

                with self.assertRaisesRegex(RuntimeError, boundary):
                    bootstrap["_persist_active"](active, self._canonical_json(new), fail_here)

                self.assertEqual(bootstrap["_read_active"](active), expected)

    def test_private_snapshot_is_unchanged_when_the_original_archive_is_replaced(self):
        """Catches validation/execution reopening a swapped archive pathname after checksum success."""
        bootstrap = runpy.run_path(str(BOOTSTRAP))
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            archive, checksum, _, _ = self._make_core(base, "9.8.7")
            replacement, _, _, _ = self._make_core(base, "9.8.8")
            snapshot, snapshot_path, digest = bootstrap["_snapshot"](archive, checksum)
            try:
                replacement.replace(archive)
                version, _ = bootstrap["_validate_archive"](snapshot, _platform_tag())
                self.assertEqual(version, "9.8.7")
                self.assertEqual(digest, hashlib.sha256(snapshot_path.read_bytes()).hexdigest())
            finally:
                os.close(snapshot)
                snapshot_path.unlink(missing_ok=True)

    def test_tampered_installed_module_is_quarantined_and_rebuilt_before_a_second_auto_run(self):
        """Catches reuse importing a modified venv package instead of rebuilding from signed wheel RECORDs."""
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            archive, checksum, manifest, signature = self._make_core(base)
            home = base / "chosen-home"
            environment = {**os.environ, "HOME": str(base / "wrong-home"), "USERPROFILE": str(base / "wrong-home")}
            first = self._run(archive, checksum, manifest, signature, home, env=environment)
            self.assertEqual(first.returncode, 0, first.stdout)
            venv = home / ".chatmaker" / "versions" / "9.8.7" / "venv"
            module = venv / ("Lib/site-packages" if os.name == "nt" else "lib/python3.11/site-packages") / "chatmaker" / "installers" / "auto.py"
            module.write_text("raise SystemExit('tampered code executed')\n", encoding="utf-8")

            repeated = self._run(archive, checksum, manifest, signature, home, env=environment)

            self.assertEqual(repeated.returncode, 0, repeated.stdout)
            self.assertEqual(json.loads(repeated.stdout)["status"], "repaired")
            self.assertFalse((base / "wrong-home" / "auto.log").exists())
            self.assertEqual((home / "auto.log").read_text(encoding="utf-8"), "auto\nauto\n")
            self.assertNotIn("tampered code executed", module.read_text(encoding="utf-8"))
            quarantines = list((home / ".chatmaker" / "quarantine").glob("9.8.7-*"))
            self.assertEqual(len(quarantines), 1)

    def test_failed_repair_activation_restores_the_previous_version(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            archive, checksum, manifest, signature = self._make_core(base)
            home = base / "home"
            first = self._run(archive, checksum, manifest, signature, home, env=os.environ.copy())
            self.assertEqual(first.returncode, 0, first.stdout)
            version_root = home / ".chatmaker" / "versions" / "9.8.7"
            module = version_root / "venv" / (
                "Lib/site-packages" if os.name == "nt" else "lib/python3.11/site-packages"
            ) / "chatmaker" / "installers" / "auto.py"
            module.write_text("# previous installed version\n", encoding="utf-8")
            bootstrap = runpy.run_path(str(self.trusted_bootstrap))
            real_replace = os.replace

            def fail_staging_activation(source, destination):
                source_path = Path(source)
                if source_path.name.startswith(".9.8.7.staging-") and Path(destination) == version_root:
                    raise OSError("simulated activation failure")
                return real_replace(source, destination)

            with mock.patch.object(bootstrap["os"], "replace", side_effect=fail_staging_activation):
                with self.assertRaisesRegex(OSError, "simulated activation failure"):
                    bootstrap["run"](
                        archive=archive,
                        checksum=checksum,
                        release_manifest=manifest,
                        release_signature=signature,
                        home=home,
                    )

            self.assertTrue(version_root.is_dir())
            self.assertEqual(module.read_text(encoding="utf-8"), "# previous installed version\n")

    def test_tampered_pyvenv_command_is_rebuilt_before_the_venv_interpreter_runs(self):
        """Catches partial pyvenv.cfg validation accepting a drifted interpreter binding record."""
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            archive, checksum, manifest, signature = self._make_core(base)
            home = base / "home"
            first = self._run(archive, checksum, manifest, signature, home, env=os.environ.copy())
            self.assertEqual(first.returncode, 0, first.stdout)
            configuration = home / ".chatmaker" / "versions" / "9.8.7" / "venv" / "pyvenv.cfg"
            lines = configuration.read_text(encoding="utf-8").splitlines()
            configuration.write_text("\n".join("command = attacker-controlled" if line.startswith("command =") else line for line in lines) + "\n", encoding="utf-8")

            repeated = self._run(archive, checksum, manifest, signature, home, env=os.environ.copy())

            self.assertEqual(repeated.returncode, 0, repeated.stdout)
            self.assertEqual(json.loads(repeated.stdout)["status"], "repaired")
            self.assertNotIn("attacker-controlled", configuration.read_text(encoding="utf-8"))

    def test_trusted_bootstrap_repairs_an_outdated_stable_launcher_template(self):
        """Catches upgrade retaining older launcher bytes merely because both files already exist."""
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            archive, checksum, manifest, signature = self._make_core(base)
            home = base / "home"
            first = self._run(archive, checksum, manifest, signature, home, env=os.environ.copy())
            self.assertEqual(first.returncode, 0, first.stdout)
            bin_root = home / ".chatmaker" / "bin"
            runner = bin_root / "chatmaker-launch.py"
            launcher = bin_root / ("chatmaker-install.cmd" if os.name == "nt" else "chatmaker-install")
            runner.write_bytes(b"outdated runner\n")
            launcher.write_bytes(b"outdated launcher\n")

            repeated = self._run(archive, checksum, manifest, signature, home, env=os.environ.copy())

            self.assertEqual(repeated.returncode, 0, repeated.stdout)
            self.assertNotEqual(runner.read_bytes(), b"outdated runner\n")
            self.assertNotEqual(launcher.read_bytes(), b"outdated launcher\n")

    def test_stable_launcher_fails_closed_on_an_invalid_active_pointer(self):
        """Catches launcher path traversal when active.json is locally malformed or attacker-edited."""
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            archive, checksum, manifest, signature = self._make_core(base)
            home = base / "home"
            first = self._run(archive, checksum, manifest, signature, home, env=os.environ.copy())
            self.assertEqual(first.returncode, 0, first.stdout)
            active = home / ".chatmaker" / "active.json"
            value = json.loads(active.read_bytes())
            value["version"] = "../escape"
            active.write_bytes(self._canonical_json(value))
            launcher = Path(json.loads(first.stdout)["launcher"])

            launched = subprocess.run(["cmd", "/d", "/c", str(launcher), "doctor"] if os.name == "nt" else [str(launcher), "doctor"], text=True, capture_output=True)

            self.assertNotEqual(launched.returncode, 0)
            self.assertIn("invalid active pointer", launched.stderr + launched.stdout)

    def test_untracked_venv_startup_hook_cannot_run_during_reuse_or_auto(self):
        """Catches sitecustomize execution before a venv has been integrity-checked."""
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            archive, checksum, manifest, signature = self._make_core(base)
            home = base / "chosen-home"
            environment = {**os.environ, "HOME": str(base / "wrong-home"), "USERPROFILE": str(base / "wrong-home")}
            first = self._run(archive, checksum, manifest, signature, home, env=environment)
            self.assertEqual(first.returncode, 0, first.stdout)
            site = home / ".chatmaker" / "versions" / "9.8.7" / "venv" / ("Lib/site-packages" if os.name == "nt" else "lib/python3.11/site-packages")
            marker = base / "startup-hook-ran"
            (site / "sitecustomize.py").write_text(f"from pathlib import Path\nPath({str(marker)!r}).write_text('unsafe')\n", encoding="utf-8")

            repeated = self._run(archive, checksum, manifest, signature, home, env=environment)

            self.assertEqual(repeated.returncode, 0, repeated.stdout)
            self.assertFalse(marker.exists())
            self.assertEqual((home / "auto.log").read_text(encoding="utf-8"), "auto\nauto\n")

    def test_untracked_module_in_site_packages_is_rejected_before_auto(self):
        """Catches an extra module shadowing a stdlib import after the wheel hashes pass."""
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            archive, checksum, manifest, signature = self._make_core(base)
            home = base / "chosen-home"
            first = self._run(archive, checksum, manifest, signature, home, env=os.environ.copy())
            self.assertEqual(first.returncode, 0, first.stdout)
            site = home / ".chatmaker" / "versions" / "9.8.7" / "venv" / ("Lib/site-packages" if os.name == "nt" else "lib/python3.11/site-packages")
            marker = base / "shadow-module-ran"
            (site / "json.py").write_text(f"from pathlib import Path\nPath({str(marker)!r}).write_text('unsafe')\nraise RuntimeError('shadowed')\n", encoding="utf-8")

            launcher = home / ".chatmaker" / "bin" / ("chatmaker-install.cmd" if os.name == "nt" else "chatmaker-install")
            launched = subprocess.run(["cmd", "/d", "/c", str(launcher), "doctor"] if os.name == "nt" else [str(launcher), "doctor"], env=os.environ.copy(), text=True, capture_output=True)
            self.assertNotEqual(launched.returncode, 0)
            self.assertFalse(marker.exists())

            repeated = self._run(archive, checksum, manifest, signature, home, env=os.environ.copy())

            self.assertEqual(repeated.returncode, 0, repeated.stdout)
            self.assertEqual(json.loads(repeated.stdout)["status"], "repaired")
            self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
