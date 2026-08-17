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


ROOT = Path(__file__).resolve().parents[2]
VERSION = "0.1.0-rc5"
EXPECTED_COMMANDS = {
    "chatmaker-doctor",
    "chatmaker-catalog",
    "chatmaker-route",
    "chatmaker-nano",
    "chatmaker-uno",
    "chatmaker-esp32",
    "chatmaker-nano-examples",
    "chatmaker-serial",
    "chatmaker-workbuddy-mcp",
    "chatmaker-install",
    "chatmaker-web",
    "chatmaker-web-plan",
    "chatmaker-web-playground",
    "chatmaker-web-preview",
    "chatmaker-web-embed",
    "chatmaker-pack",
    "chatmaker-knowledge",
}


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

    def test_extracted_core_bootstrap_installs_the_versioned_runtime_and_runs_auto(self):
        """Catches a release whose bundled bootstrap cannot start from a fresh user HOME."""
        with tempfile.TemporaryDirectory(prefix="chatmaker-bootstrap-clean-") as directory:
            base = Path(directory)
            build = base / "build"
            extract = base / "extract"
            home = base / "fresh 用户 home"
            build.mkdir()
            extract.mkdir()
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
                    ],
                    cwd=ROOT,
                    env=os.environ.copy(),
                ).stdout
            )
            with zipfile.ZipFile(build_result["archive"]) as archive:
                archive.extractall(extract)
            core = extract / f"ChatMaker-Core-{VERSION}"
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
                        str(core / "scripts" / "bootstrap.py"),
                        "--archive",
                        str(build_result["archive"]),
                        "--checksum",
                        str(build_result["checksum_file"]),
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
            self.assertEqual(result["auto"]["status"], "ready_with_limits")
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
                    ],
                    cwd=ROOT,
                    env=os.environ.copy(),
                ).stdout
            )
            with zipfile.ZipFile(build_result["archive"]) as archive:
                archive.extractall(extract)
            core = extract / f"ChatMaker-Core-{VERSION}"

            self.assertEqual(
                {path.name for path in (core / "skills").iterdir() if path.is_dir()},
                {"chatmaker", "chatduino", "chatweb"},
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
            for name in sorted(EXPECTED_COMMANDS - {"chatmaker-workbuddy-mcp"}):
                self._run(
                    [str(self._command(venv, name)), "--help"],
                    cwd=core,
                    env=env,
                )

            mcp = json.loads(
                self._run(
                    [str(self._command(venv, "chatmaker-workbuddy-mcp"))],
                    cwd=core,
                    env=env,
                    input_text='{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}\n',
                ).stdout
            )
            self.assertEqual(mcp["id"], 1)
            self.assertEqual(len(mcp["result"]["tools"]), 24)

            doctor = json.loads(
                self._run(
                    [str(self._command(venv, "chatmaker-doctor"))],
                    cwd=core,
                    env=env,
                ).stdout
            )
            self.assertEqual(
                doctor["packs"]["counts"],
                {"board": 3, "component": 12, "recipe": 14},
            )
            self.assertEqual(doctor["packs"]["knowledge_indexes"], 3)
            self.assertEqual(
                set(doctor["skills"]["results"]),
                {"chatmaker", "chatduino", "chatweb"},
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
            installed = json.loads(
                self._run(
                    [str(installer), "auto"],
                    cwd=core,
                    env=env,
                ).stdout
            )
            self.assertTrue(installed["success"])
            self.assertEqual([host["host"] for host in installed["hosts"]], ["codex", "workbuddy"])
            self.assertTrue(json.loads(self._run(
                [str(installer), "doctor"],
                cwd=core,
                env=env,
            ).stdout)["success"])
            self.assertTrue(json.loads(self._run(
                [str(installer), "uninstall"],
                cwd=core,
                env=env,
            ).stdout)["success"])
            self.assertFalse(any((codex_home / "skills").glob("*")))
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
