from __future__ import annotations

import hashlib
import importlib.util
import tempfile
import tomllib
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RELEASE_VERSION = "0.1.0-rc4"


def load_builder():
    path = ROOT / "scripts" / "build_release.py"
    spec = importlib.util.spec_from_file_location("chatmaker_build_release", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ReleasePackageTests(unittest.TestCase):
    def test_release_zip_is_deterministic_and_contains_installable_project(self):
        builder = load_builder()
        with tempfile.TemporaryDirectory() as directory:
            first = builder.build_release(ROOT, Path(directory) / "first", RELEASE_VERSION)
            second = builder.build_release(ROOT, Path(directory) / "second", RELEASE_VERSION)

            first_zip = Path(first["archive"])
            second_zip = Path(second["archive"])
            first_hash = hashlib.sha256(first_zip.read_bytes()).hexdigest()
            second_hash = hashlib.sha256(second_zip.read_bytes()).hexdigest()
            with zipfile.ZipFile(first_zip) as archive:
                names = set(archive.namelist())

        prefix = f"ChatMaker-{RELEASE_VERSION}/"
        metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(metadata["project"]["version"], "0.1.0rc4")
        self.assertEqual(first_hash, second_hash)
        self.assertEqual(first_hash, first["sha256"])
        self.assertIn(prefix + "README.md", names)
        self.assertIn(prefix + "CONTRIBUTING.md", names)
        self.assertIn(prefix + "RELEASE_NOTES.md", names)
        self.assertIn(prefix + "pyproject.toml", names)
        self.assertIn(prefix + "docs/installation.md", names)
        self.assertIn(prefix + "docs/demo/one-minute-demo.md", names)
        self.assertIn(prefix + ".github/pull_request_template.md", names)
        self.assertIn(prefix + "skills/chatmaker/SKILL.md", names)
        self.assertIn(prefix + "runtime/chatmaker/installers/codex.py", names)
        self.assertFalse(any("__pycache__" in name or ".git/" in name for name in names))


if __name__ == "__main__":
    unittest.main()
