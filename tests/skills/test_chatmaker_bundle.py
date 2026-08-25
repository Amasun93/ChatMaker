from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def load_builder():
    path = ROOT / "scripts" / "build_chatmaker_skill_bundle.py"
    spec = importlib.util.spec_from_file_location("build_chatmaker_skill_bundle", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ChatMakerBundleTests(unittest.TestCase):
    def test_bundle_contains_exact_router_and_internal_specialist_files(self):
        builder = load_builder()
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "chatmaker"
            result = builder.build_bundle(ROOT, output)
            expected = {
                relative.as_posix(): builder._sha256(source)
                for relative, source in builder.source_map(ROOT).items()
            }
            self.assertTrue(result["success"])
            self.assertEqual(result["manifest"], expected)
            self.assertEqual(builder.bundle_manifest(output), expected)
            self.assertTrue((output / "agents" / "openai.yaml").is_file())
            for name in builder.SPECIALISTS:
                self.assertTrue((output / "internal_skills" / name / "SKILL.md").is_file())

    def test_rebuild_replaces_stale_bundle_without_leaving_extra_files(self):
        builder = load_builder()
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "chatmaker"
            output.mkdir()
            (output / "stale.txt").write_text("old", encoding="utf-8")
            builder.build_bundle(ROOT, output)
            self.assertFalse((output / "stale.txt").exists())
            self.assertFalse(output.with_name(".chatmaker.previous").exists())


if __name__ == "__main__":
    unittest.main()
