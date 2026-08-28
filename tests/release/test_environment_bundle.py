from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[2]


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_environment_bundle", ROOT / "scripts/build_environment_bundle.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class EnvironmentBundleTests(unittest.TestCase):
    def test_build_is_deterministic_and_contains_offline_python_and_core(self):
        builder = load_builder()
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            registry = source / "runtime/chatmaker/installers/runtime_sources.json"
            registry.parent.mkdir(parents=True)
            installer = source / "scripts/install_environment_bundle.ps1"
            installer.parent.mkdir(parents=True)
            installer.write_text("Write-Output 'install'\n", encoding="utf-8")
            python = base / "python-offline.zip"
            python.write_bytes(b"portable-python")
            registry.write_text(
                json.dumps(
                    {
                        "python": {
                            "windows-amd64": {
                                "version": "3.11.10",
                                "filename": python.name,
                                "size": python.stat().st_size,
                                "sha256": hashlib.sha256(python.read_bytes()).hexdigest(),
                                "archive_root": "python",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            core = base / "ChatMaker-Core-1.2.3-windows-amd64.zip"
            with zipfile.ZipFile(core, "w") as archive:
                archive.writestr(
                    "ChatMaker-Core-1.2.3-windows-amd64/scripts/setup_local_runtime.ps1",
                    "Write-Output 'setup'\n",
                )
                archive.writestr(
                    "ChatMaker-Core-1.2.3-windows-amd64/core-runtime/requirements.txt",
                    "example==1\n",
                )
            first = builder.build_environment_bundle(
                source_root=source,
                core_archive=core,
                python_archive=python,
                output_dir=base / "first",
                version="1.2.3",
            )
            second = builder.build_environment_bundle(
                source_root=source,
                core_archive=core,
                python_archive=python,
                output_dir=base / "second",
                version="1.2.3",
            )
            first_archive = Path(first["archive"])
            second_archive = Path(second["archive"])
            self.assertEqual(first_archive.read_bytes(), second_archive.read_bytes())
            prefix = "ChatMaker-Environment-1.2.3-windows-amd64/"
            with zipfile.ZipFile(first_archive) as archive:
                names = set(archive.namelist())
                manifest = json.loads(archive.read(prefix + "environment-manifest.json"))
            self.assertIn(prefix + "install.ps1", names)
            self.assertIn(prefix + "cache/python-offline.zip", names)
            self.assertIn(prefix + "core/scripts/setup_local_runtime.ps1", names)
            self.assertEqual(manifest["contents"]["node"], "not-included")
            self.assertEqual(manifest["python"]["version"], "3.11.10")

    def test_rejects_python_bytes_that_do_not_match_the_source_registry(self):
        builder = load_builder()
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            registry = source / "runtime/chatmaker/installers/runtime_sources.json"
            registry.parent.mkdir(parents=True)
            (source / "scripts").mkdir()
            (source / "scripts/install_environment_bundle.ps1").write_text("", encoding="utf-8")
            python = base / "python.zip"
            python.write_bytes(b"wrong")
            registry.write_text(
                json.dumps(
                    {
                        "python": {
                            "windows-amd64": {
                                "version": "3.11.10",
                                "filename": python.name,
                                "size": python.stat().st_size,
                                "sha256": "0" * 64,
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            core = base / "ChatMaker-Core-1.2.3-windows-amd64.zip"
            core.write_bytes(b"not reached")
            with self.assertRaisesRegex(builder.EnvironmentBundleError, "python_archive_identity_mismatch"):
                builder.build_environment_bundle(
                    source_root=source,
                    core_archive=core,
                    python_archive=python,
                    output_dir=base / "out",
                    version="1.2.3",
                )


if __name__ == "__main__":
    unittest.main()
