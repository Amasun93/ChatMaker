"""Network-free clean-Core install and first-use integration test.

The venv is fresh but intentionally inherits the invoking interpreter's
already-installed third-party dependencies.  The extracted Core itself is
installed editable by setuptools ``develop --no-deps``.  This avoids package
index access and also avoids requiring the optional ``wheel`` package merely
to test an extracted source Core.  HOME, USERPROFILE, host configuration,
ChatMaker state, temp files and installer targets all stay under one temporary
directory.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
import zipfile

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[2]
VERSION = "0.1.0-rc5"
PLATFORM_TAG = "windows-amd64" if os.name == "nt" else "macos-arm64" if os.uname().machine in {"arm64", "aarch64"} else "macos-x86_64"
EXPECTED_COMMANDS = {
    "chatmaker-doctor",
    "chatmaker-catalog",
    "chatmaker-route",
    "chatmaker-board-identify",
    "chatmaker-nano",
    "chatmaker-uno",
    "chatmaker-esp32",
    "chatmaker-nano-examples",
    "chatmaker-serial",
    "chatmaker-avr-project",
    "chatmaker-starcore",
    "chatmaker-mpython",
    "chatmaker-mpython-v3",
    "chatmaker-stardust",
    "chatmaker-microbit",
    "chatmaker-unihiker",
    "chatmaker-install",
    "chatmaker-web",
    "chatmaker-web-plan",
    "chatmaker-web-playground",
    "chatmaker-web-preview",
    "chatmaker-web-embed",
    "chatmaker-pack",
    "chatmaker-knowledge",
    "chatmaker-feedback",
    "chatmaker-cad",
}


def prepared_runtime(root: Path) -> Path:
    prepared = root / "prepared"
    wheelhouse = prepared / "wheelhouse"
    wheelhouse.mkdir(parents=True, exist_ok=True)
    wheel = wheelhouse / "chatmaker-0.1.0rc5-py3-none-any.whl"
    payloads = {
        "chatmaker/__init__.py": b"",
        "chatmaker/installers/__init__.py": b"",
        "chatmaker/installers/local.py": b"import json\ndef main(argv=None): print(json.dumps({'success':True,'status':'local_ready_with_limits','host_scan_performed':False})); return 0\nif __name__ == '__main__': raise SystemExit(main())\n",
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
    digest = __import__("hashlib").sha256(wheel.read_bytes()).hexdigest()
    manifest = {"schema_version": 2, "platform_tag": PLATFORM_TAG, "python_requires": "==3.11.*", "core_wheel": wheel.name, "wheels": [{"filename": wheel.name, "project": "chatmaker", "version": "0.1.0rc5", "size": wheel.stat().st_size, "sha256": digest, "tags": ["py3-none-any"], "requires": []}]}
    (prepared / "manifest.json").write_bytes((json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii"))
    (prepared / "requirements.txt").write_bytes(f"chatmaker==0.1.0rc5 --hash=sha256:{digest}\n".encode("ascii"))
    return prepared


def signed_test_bootstrap(root: Path, release_manifest: Path) -> tuple[Path, Path]:
    """Create a trusted-bootstrap test copy anchored to an ephemeral key; CLI has no override."""
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    trusted = root / "trusted-bootstrap"
    trusted.mkdir()
    shutil.copy2(ROOT / "scripts" / "bootstrap.py", trusted / "bootstrap.py")
    verifier = (ROOT / "scripts" / "core_release_signature.py").read_text(encoding="utf-8")
    verifier = verifier.replace(
        "89b25c42329e5deff966621a115f479883b78fd3db5610f34a5600f4e8fd1da9",
        public.hex(),
    ).replace(
        "70570b179cf452abcc7486f76a408a25faee3702433663e99b7418498d725f67",
        hashlib.sha256(public).hexdigest(),
    )
    (trusted / "core_release_signature.py").write_text(verifier, encoding="utf-8", newline="\n")
    manifest_bytes = release_manifest.read_bytes()
    detached = {
        "algorithm": "ed25519",
        "key_id": "chatmaker-official-2026-01",
        "signature": base64.b64encode(key.sign(b"ChatMaker Core Release Manifest v1\0" + manifest_bytes)).decode("ascii"),
    }
    signature = root / "release.sig.json"
    signature.write_bytes((json.dumps(detached, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii"))
    return trusted / "bootstrap.py", signature


class CleanCoreIntegrationTests(unittest.TestCase):
    maxDiff = None

    def _run(
        self,
        command: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        input_text: str | None = None,
        timeout: int = 180,
    ) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                command,
                cwd=cwd,
                env=env,
                input=input_text,
                text=True,
                capture_output=True,
                check=True,
                timeout=timeout,
            )
        except subprocess.CalledProcessError as exc:
            raise AssertionError(
                f"command failed ({exc.returncode}): {command!r}\n"
                f"stdout:\n{exc.stdout}\nstderr:\n{exc.stderr}"
            ) from exc

    @staticmethod
    def _command(venv: Path, name: str) -> Path:
        scripts = venv / ("Scripts" if os.name == "nt" else "bin")
        suffix = ".exe" if os.name == "nt" else ""
        return scripts / f"{name}{suffix}"

    def test_extracted_core_bootstrap_installs_the_versioned_runtime_and_runs_local_check(self):
        """Catches a release whose bundled bootstrap cannot start from a fresh user HOME."""
        with tempfile.TemporaryDirectory(prefix="chatmaker-bootstrap-clean-") as directory:
            base = Path(directory)
            build = base / "build"
            extract = base / "extract"
            home = base / "fresh 用户 home"
            build.mkdir()
            extract.mkdir()
            prepared = prepared_runtime(base)
            build_result = json.loads(
                self._run(
                    [
                        sys.executable,
                        str(ROOT / "scripts" / "build_release.py"),
                        "--root",
                        str(ROOT),
                        "--output",
                        str(build),
                        "--version",
                        VERSION,
                        "--platform-tag",
                        PLATFORM_TAG,
                        "--prepared-root",
                        str(prepared),
                    ],
                    cwd=ROOT,
                    env=os.environ.copy(),
                ).stdout
            )
            with zipfile.ZipFile(build_result["archive"]) as archive:
                archive.extractall(extract)
            core = extract / f"ChatMaker-Core-{VERSION}-{PLATFORM_TAG}"
            trusted_bootstrap, release_signature = signed_test_bootstrap(base, Path(build_result["release_manifest"]))
            environment = os.environ.copy()
            environment.update(
                {
                    "HOME": str(home),
                    "USERPROFILE": str(home),
                    "PIP_CONFIG_FILE": os.devnull,
                    "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                    "PIP_NO_INDEX": "1",
                    "PYTHONNOUSERSITE": "1",
                    "TMP": str(base / "tmp"),
                    "TEMP": str(base / "tmp"),
                }
            )
            environment.pop("PYTHONPATH", None)
            (base / "tmp").mkdir()
            result = json.loads(
                self._run(
                    [
                        sys.executable,
                        str(trusted_bootstrap),
                        "--archive",
                        str(build_result["archive"]),
                        "--checksum",
                        str(build_result["checksum_file"]),
                        "--release-manifest",
                        str(build_result["release_manifest"]),
                        "--release-signature",
                        str(release_signature),
                        "--home",
                        str(home),
                    ],
                    cwd=base,
                    env=environment,
                    timeout=240,
                ).stdout
            )

            self.assertTrue(result["success"])
            self.assertEqual(result["status"], "installed")
            self.assertIn(result["local_check"]["status"], {"local_ready", "local_ready_with_limits"})
            self.assertTrue(Path(result["venv"]).is_dir())
            self.assertTrue(Path(result["launcher"]).is_file())

    def test_extracted_core_installs_and_operates_in_fresh_home(self):
        with tempfile.TemporaryDirectory(prefix="chatmaker-clean-core-") as directory:
            base = Path(directory)
            build = base / "build"
            extract = base / "extract"
            home = base / "home"
            venv = base / "venv"
            build.mkdir()
            extract.mkdir()
            home.mkdir()
            prepared = prepared_runtime(base)

            build_result = json.loads(
                self._run(
                    [
                        sys.executable,
                        str(ROOT / "scripts" / "build_release.py"),
                        "--root",
                        str(ROOT),
                        "--output",
                        str(build),
                        "--version",
                        VERSION,
                        "--platform-tag",
                        PLATFORM_TAG,
                        "--prepared-root",
                        str(prepared),
                    ],
                    cwd=ROOT,
                    env=os.environ.copy(),
                ).stdout
            )
            with zipfile.ZipFile(build_result["archive"]) as archive:
                archive.extractall(extract)
            core = extract / f"ChatMaker-Core-{VERSION}-{PLATFORM_TAG}"

            self.assertEqual(
                {path.name for path in (core / "skills").iterdir() if path.is_dir()},
                {"chatmaker", "chatduino", "chatweb", "chatcad"},
            )
            self.assertFalse(any((core / "knowledge").rglob("*.md")))
            for excluded in (
                "knowledge_sources",
                "tests",
                "distribution",
                "CONTRIBUTING.md",
                "RELEASE_NOTES.md",
            ):
                self.assertFalse((core / excluded).exists(), excluded)

            self._run(
                [
                    sys.executable,
                    "-m",
                    "venv",
                    "--system-site-packages",
                    str(venv),
                ],
                cwd=base,
                env=os.environ.copy(),
            )
            python = self._command(venv, "python")
            env = os.environ.copy()
            env.update(
                {
                    "HOME": str(home),
                    "USERPROFILE": str(home),
                    "CODEX_HOME": str(home / ".codex-default-unused"),
                    "CHATMAKER_PACKS_PATH": "",
                    "PIP_CONFIG_FILE": os.devnull,
                    "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                    "PIP_NO_INDEX": "1",
                    "PYTHONNOUSERSITE": "1",
                    "TMP": str(base / "tmp"),
                    "TEMP": str(base / "tmp"),
                }
            )
            env.pop("PYTHONPATH", None)
            (base / "tmp").mkdir()
            self._run(
                [
                    str(python),
                    "-c",
                    "from setuptools import setup; setup()",
                    "--no-user-cfg",
                    "develop",
                    "--no-deps",
                ],
                cwd=core,
                env=env,
            )

            imported = Path(
                self._run(
                    [str(python), "-c", "import chatmaker; print(chatmaker.__file__)"],
                    cwd=core,
                    env=env,
                ).stdout.strip()
            ).resolve()
            self.assertTrue(imported.is_relative_to(core.resolve()), imported)

            metadata = tomllib.loads((core / "pyproject.toml").read_text(encoding="utf-8"))
            self.assertEqual(set(metadata["project"]["scripts"]), EXPECTED_COMMANDS)
            for name in sorted(EXPECTED_COMMANDS):
                self.assertTrue(self._command(venv, name).is_file(), name)
            for name in sorted(EXPECTED_COMMANDS):
                self._run(
                    [str(self._command(venv, name)), "--help"],
                    cwd=core,
                    env=env,
                )

            doctor = json.loads(
                self._run(
                    [str(self._command(venv, "chatmaker-doctor"))],
                    cwd=core,
                    env=env,
                ).stdout
            )
            self.assertEqual(
                doctor["packs"]["counts"],
                {"board": 9, "component": 35, "recipe": 30},
            )
            self.assertEqual(doctor["packs"]["knowledge_indexes"], 8)
            self.assertEqual(
                set(doctor["skills"]["results"]),
                {"chatmaker", "chatduino", "chatweb", "chatcad"},
            )

            catalog = json.loads(
                self._run(
                    [
                        str(self._command(venv, "chatmaker-catalog")),
                        "--request-json",
                        '{"action":"open_board","board_id":"arduino-nano-classic"}',
                    ],
                    cwd=core,
                    env=env,
                ).stdout
            )
            self.assertTrue(catalog["success"])
            route = json.loads(
                self._run(
                    [
                        str(self._command(venv, "chatmaker-route")),
                        "--request-json",
                        (
                            '{"goal":"Blink a real LED from an Arduino Nano",'
                            '"hardware":{"board":"arduino-nano-classic",'
                            '"physical_effect":"The LED blinks on the desk."}}'
                        ),
                    ],
                    cwd=core,
                    env=env,
                ).stdout
            )
            self.assertTrue(route["success"])
            self.assertEqual(route["specialists"], ["chatduino"])
            index = json.loads(
                self._run(
                    [
                        str(self._command(venv, "chatmaker-knowledge")),
                        "--request-json",
                        '{"action":"index","board_id":"arduino-nano-classic","consumer":"chatduino"}',
                    ],
                    cwd=core,
                    env=env,
                ).stdout
            )
            self.assertTrue(index["success"])
            self.assertTrue(all(not item["available"] for item in index["sections"]))

            codex_home = home / "host-codex"
            (codex_home / "skills").mkdir(parents=True)
            workbuddy_config = home / "host-workbuddy" / "mcp.json"
            workbuddy_config.parent.mkdir(parents=True)
            original_config = {
                "mcpServers": {"unrelated": {"command": "keep-me"}},
                "hostSetting": True,
            }
            workbuddy_config.write_text(
                json.dumps(original_config, indent=2) + "\n", encoding="utf-8"
            )
            env.update(
                {
                    "CODEX_HOME": str(codex_home),
                    "WORKBUDDY_HOME": str(workbuddy_config.parent),
                    "WORKBUDDY_CONFIG": str(workbuddy_config),
                }
            )
            installer = self._command(venv, "chatmaker-install")
            local_check = json.loads(
                self._run(
                    [str(installer), "local"],
                    cwd=core,
                    env=env,
                ).stdout
            )
            self.assertTrue(local_check["success"])
            self.assertFalse(local_check["host_scan_performed"])
            self.assertNotIn("hosts", local_check)
            self.assertFalse(any((codex_home / "skills").glob("*")))
            self.assertTrue(json.loads(self._run(
                [str(installer), "doctor"],
                cwd=core,
                env=env,
            ).stdout)["success"])
            self.assertEqual(
                json.loads(workbuddy_config.read_text(encoding="utf-8")),
                original_config,
            )

            pack_source = base / "pack-source"
            pack_sections = pack_source / "knowledge" / "sections"
            pack_sections.mkdir(parents=True)
            shutil.copy2(
                ROOT / "knowledge" / "boards" / "arduino-nano-classic.yaml",
                pack_source / "knowledge" / "index.yaml",
            )
            for page in (
                ROOT / "knowledge_sources" / "published" / "boards" / "arduino-nano-classic"
            ).glob("*.md"):
                shutil.copy2(page, pack_sections / page.name)
            pack = build / "chatmaker-board-arduino-nano-classic-knowledge-1.0.0.cmpack"
            self._run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_pack.py"),
                    "--source",
                    str(pack_source),
                    "--output",
                    str(pack),
                    "--pack-id",
                    "chatmaker-board-arduino-nano-classic-knowledge",
                    "--pack-version",
                    "1.0.0",
                    "--board-id",
                    "arduino-nano-classic",
                    "--core-minimum",
                    "0.1.0",
                    "--core-maximum-exclusive",
                    "0.2.0",
                ],
                cwd=ROOT,
                env=os.environ.copy(),
            )
            probe = json.loads(
                self._run(
                    [
                        str(python),
                        str(ROOT / "tests" / "release" / "clean_core_probe.py"),
                        "--core-root",
                        str(core),
                        "--pack",
                        str(pack),
                        "--user-root",
                        str(home / ".chatmaker-fixture"),
                    ],
                    cwd=core,
                    env=env,
                ).stdout
            )
            self.assertEqual(probe["first_fetch_count"], 3)
            self.assertEqual(probe["second_fetch_count"], 3)
            self.assertTrue(probe["offline_success"])


if __name__ == "__main__":
    unittest.main()
