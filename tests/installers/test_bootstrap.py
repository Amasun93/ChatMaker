from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = ROOT / "scripts" / "bootstrap.py"


def _symlink_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name)
    info.create_system = 3
    info.external_attr = (0o120777 << 16)
    return info


class BootstrapTests(unittest.TestCase):
    """End-to-end contracts for the stdlib-only Core bootstrapper."""

    def _make_core(self, directory: Path, version: str = "9.8.7") -> tuple[Path, Path]:
        """Build a tiny, real installable Core archive with a local console entry point."""
        root = directory / f"ChatMaker-Core-{version}"
        package = root / "runtime" / "chatmaker"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "installer.py").write_text(
            "from __future__ import annotations\n"
            "import json, os\n"
            "from pathlib import Path\n"
            "def main():\n"
            "    log = os.environ.get('CHATMAKER_AUTO_LOG')\n"
            "    if log:\n"
            "        with Path(log).open('a', encoding='utf-8') as stream:\n"
            "            stream.write('auto\\n')\n"
            "    if os.environ.get('CHATMAKER_AUTO_FAIL'):\n"
            "        print(json.dumps({'success': False, 'status': 'failed', 'detail': 'fixture failure'}))\n"
            "        return 2\n"
            "    print(json.dumps({'success': True, 'status': 'ready_with_limits'}))\n"
            "    return 0\n",
            encoding="utf-8",
        )
        (root / "pyproject.toml").write_text(
            "[build-system]\nrequires = ['setuptools>=68']\nbuild-backend = 'setuptools.build_meta'\n"
            f"[project]\nname = 'chatmaker'\nversion = '{version}'\n"
            "[project.scripts]\nchatmaker-install = 'chatmaker.installer:main'\n"
            "[tool.setuptools]\npackage-dir = {'' = 'runtime'}\n"
            "[tool.setuptools.packages.find]\nwhere = ['runtime']\n",
            encoding="utf-8",
        )
        scripts = root / "scripts"
        scripts.mkdir()
        (scripts / "bootstrap.py").write_text("# release bootstrap\n", encoding="utf-8")
        archive = directory / f"ChatMaker-Core-{version}.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    bundle.write(path, path.relative_to(directory).as_posix())
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        checksum = directory / f"{archive.name}.sha256"
        checksum.write_text(f"{digest}  {archive.name}\n", encoding="ascii")
        return archive, checksum

    @staticmethod
    def _run(archive: Path, checksum: Path, home: Path, *, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(BOOTSTRAP),
                "--archive",
                str(archive),
                "--checksum",
                str(checksum),
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
            archive, checksum = self._make_core(base)
            home = base / "老师 的 ChatMaker 家目录"
            auto_log = base / "auto.log"
            environment = os.environ.copy()
            environment.update(
                {
                    "HOME": str(home),
                    "USERPROFILE": str(home),
                    "PIP_NO_INDEX": "1",
                    "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                    "CHATMAKER_AUTO_LOG": str(auto_log),
                }
            )

            first = self._run(archive, checksum, home, env=environment)
            self.assertEqual(first.returncode, 0, first.stderr)
            installed = json.loads(first.stdout)
            self.assertTrue(installed["success"])
            self.assertEqual(installed["status"], "installed")
            venv = home / ".chatmaker" / "versions" / "9.8.7" / "venv"
            self.assertEqual(Path(installed["venv"]), venv)
            self.assertTrue(venv.is_dir())
            launcher = Path(installed["launcher"])
            self.assertTrue(launcher.is_file())
            python = venv / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")
            imported = subprocess.run(
                [str(python), "-c", "import chatmaker; print(chatmaker.__file__)"],
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertTrue(Path(imported.stdout.strip()).resolve().is_relative_to(venv.resolve()))
            before = (home / ".chatmaker" / "versions" / "9.8.7" / ".bootstrap.json").read_bytes()

            second = self._run(archive, checksum, home, env=environment)
            self.assertEqual(second.returncode, 0, second.stderr)
            repeated = json.loads(second.stdout)
            self.assertTrue(repeated["success"])
            self.assertEqual(repeated["status"], "already_current")
            self.assertEqual(before, (home / ".chatmaker" / "versions" / "9.8.7" / ".bootstrap.json").read_bytes())
            launcher_command = ["cmd", "/d", "/c", str(launcher), "auto"] if os.name == "nt" else [str(launcher), "auto"]
            launched = subprocess.run(launcher_command, env=environment, text=True, capture_output=True)
            self.assertEqual(launched.returncode, 0, launched.stderr)
            self.assertEqual(auto_log.read_text(encoding="utf-8"), "auto\nauto\nauto\n")

    def test_bootstrap_rejects_a_bad_checksum_before_creating_its_install_root(self):
        """Catches unpacking or creating a version directory before archive identity is proven."""
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            archive, checksum = self._make_core(base)
            checksum.write_text("0" * 64 + f"  {archive.name}\n", encoding="ascii")
            home = base / "home"
            result = self._run(archive, checksum, home, env=os.environ.copy())

            self.assertNotEqual(result.returncode, 0)
            report = json.loads(result.stdout)
            self.assertFalse(report["success"])
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["error"], "BootstrapError")
            self.assertFalse((home / ".chatmaker" / "versions").exists())

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
            home = base / "home"
            result = self._run(archive, checksum, home, env=os.environ.copy())

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
                home = base / f"home-{name}"
                result = self._run(archive, checksum, home, env=os.environ.copy())
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(json.loads(result.stdout)["error"], "BootstrapError")
                self.assertFalse((home / ".chatmaker" / "versions").exists())

    def test_failed_new_version_leaves_the_previous_active_launcher_unchanged(self):
        """Catches a failed auto convergence switching the active user launcher too early."""
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            first_archive, first_checksum = self._make_core(base, "9.8.7")
            second_archive, second_checksum = self._make_core(base, "9.8.8")
            home = base / "home"
            environment = os.environ.copy()
            environment.update({"HOME": str(home), "USERPROFILE": str(home), "PIP_NO_INDEX": "1"})

            first = self._run(first_archive, first_checksum, home, env=environment)
            self.assertEqual(first.returncode, 0, first.stdout)
            active = home / ".chatmaker" / "active.json"
            launcher = Path(json.loads(first.stdout)["launcher"])
            active_before = active.read_bytes()
            launcher_before = launcher.read_bytes()

            failed_environment = dict(environment)
            failed_environment["CHATMAKER_AUTO_FAIL"] = "1"
            failed = self._run(second_archive, second_checksum, home, env=failed_environment)

            self.assertNotEqual(failed.returncode, 0)
            self.assertFalse(json.loads(failed.stdout)["success"])
            self.assertEqual(active.read_bytes(), active_before)
            self.assertEqual(launcher.read_bytes(), launcher_before)


if __name__ == "__main__":
    unittest.main()
