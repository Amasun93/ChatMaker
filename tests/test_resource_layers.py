from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))


try:
    from chatmaker.resources import ResourceResolver, resource_generation_token
except ImportError:
    ResourceResolver = None
    resource_generation_token = None


PACK_ID = "chatmaker-board-arduino-nano-classic-wiki"
RESOURCE = "llmwiki/sections/start-here.md"


class _VerifiedManager:
    def __init__(self, root: Path, version: str = "1.0.0") -> None:
        self.root = root
        self.version = version

    def active_resource_root(self, pack_id: str) -> tuple[Path, str] | None:
        if pack_id != PACK_ID:
            return None
        return self.root, self.version

    def generation_token(self) -> str:
        return "7:verified-active-state"


class ResourceLayerTests(unittest.TestCase):
    def setUp(self) -> None:
        if ResourceResolver is None or resource_generation_token is None:
            self.fail("Task 4 resource layer is missing")
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.user_root = self.root / "user"
        self.builtin_root = self.root / "builtin"
        self.official_root = self.root / "official"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    @staticmethod
    def _write(root: Path, relative: str, body: str) -> Path:
        path = root / Path(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def test_explicit_path_precedes_user_override_official_and_builtin(self):
        explicit = self.root / "explicit"
        self._write(explicit / PACK_ID, RESOURCE, "explicit")
        self._write(self.user_root / "overrides" / PACK_ID, RESOURCE, "user")
        self._write(self.official_root, RESOURCE, "official")
        self._write(self.builtin_root / PACK_ID, RESOURCE, "builtin")

        resolver = ResourceResolver(
            user_root=self.user_root,
            builtin_root=self.builtin_root,
            manager=_VerifiedManager(self.official_root),
            environ={"CHATMAKER_PACKS_PATH": str(explicit)},
        )
        resolved = resolver.resolve(RESOURCE, pack_id=PACK_ID)

        self.assertEqual(resolved.read_text(), "explicit")
        self.assertEqual(
            resolved.provenance,
            {
                "kind": "local_override",
                "path": f"{PACK_ID}/{RESOURCE}",
            },
        )

    def test_user_override_remains_effective_and_is_labelled(self):
        override = self._write(
            self.user_root / "overrides" / PACK_ID, RESOURCE, "override"
        )
        self._write(self.official_root, RESOURCE, "official")
        before = override.read_bytes()

        resolved = ResourceResolver(
            user_root=self.user_root,
            builtin_root=self.builtin_root,
            manager=_VerifiedManager(self.official_root),
            environ={},
        ).resolve(RESOURCE, pack_id=PACK_ID)

        self.assertEqual(resolved.read_text(), "override")
        self.assertEqual(resolved.provenance["kind"], "local_override")
        self.assertEqual(override.read_bytes(), before)

    def test_verified_official_and_builtin_report_distinct_provenance(self):
        self._write(self.official_root, RESOURCE, "official")
        self._write(self.builtin_root / PACK_ID, RESOURCE, "builtin")
        resolver = ResourceResolver(
            user_root=self.user_root,
            builtin_root=self.builtin_root,
            manager=_VerifiedManager(self.official_root, "2.3.0"),
            environ={},
        )

        official = resolver.resolve(RESOURCE, pack_id=PACK_ID)
        self.assertEqual(official.read_text(), "official")
        self.assertEqual(
            official.provenance,
            {"kind": "official_pack", "pack_id": PACK_ID, "version": "2.3.0"},
        )

        (self.official_root / Path(*RESOURCE.split("/"))).unlink()
        manager_without_active = _VerifiedManager(self.root / "absent")
        manager_without_active.active_resource_root = lambda pack_id: None
        builtin = ResourceResolver(
            user_root=self.user_root,
            builtin_root=self.builtin_root,
            manager=manager_without_active,
            environ={},
            core_version="0.1.0",
        ).resolve(RESOURCE, pack_id=PACK_ID)
        self.assertEqual(builtin.read_text(), "builtin")
        self.assertEqual(
            builtin.provenance,
            {"kind": "builtin_core", "core_version": "0.1.0"},
        )

    def test_generation_token_changes_with_active_state_bytes(self):
        state = self.user_root / "state" / "active.json"
        state.parent.mkdir(parents=True)
        state.write_text(
            json.dumps({"schema_version": "1.0", "generation": 1, "packs": {}}),
            encoding="utf-8",
        )
        first = resource_generation_token(self.user_root)
        state.write_text(
            json.dumps({"schema_version": "1.0", "generation": 2, "packs": {}}),
            encoding="utf-8",
        )
        second = resource_generation_token(self.user_root)

        self.assertTrue(first.startswith("1:"))
        self.assertTrue(second.startswith("2:"))
        self.assertNotEqual(first, second)

    def test_rejects_traversal_instead_of_reading_outside_a_layer(self):
        outside = self._write(self.root, "secret.md", "secret")
        resolver = ResourceResolver(
            user_root=self.user_root,
            builtin_root=self.builtin_root,
            manager=None,
            environ={"CHATMAKER_PACKS_PATH": str(self.root / "explicit")},
        )
        with self.assertRaises(ValueError):
            resolver.resolve("../secret.md", pack_id=PACK_ID)
        self.assertEqual(outside.read_text(encoding="utf-8"), "secret")


if __name__ == "__main__":
    unittest.main()
