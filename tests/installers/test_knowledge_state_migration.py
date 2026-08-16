from __future__ import annotations

from concurrent.futures import (
    ThreadPoolExecutor,
    TimeoutError as FutureTimeoutError,
)
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from runtime.chatmaker.installers.knowledge_state_migration import (
    KnowledgeStateMigrationError,
    migrate_legacy_knowledge_state,
)
from runtime.chatmaker.installers.file_lock import exclusive_file_lock
from runtime.chatmaker.installers.pack_manager import PackManager, PackPaths


LEGACY_NANO = "chatmaker-board-arduino-nano-classic-wiki"
LEGACY_UNO = "chatmaker-board-arduino-uno-r3-wiki"
CURRENT_NANO = "chatmaker-board-arduino-nano-classic-knowledge"
UNKNOWN_PACK = "third-party-board-knowledge"
SHA_A = "a" * 64
SHA_B = "b" * 64


def _active_bytes(*, packs: dict[str, object], generation: int = 7) -> bytes:
    return (
        json.dumps(
            {"schema_version": "1.0", "generation": generation, "packs": packs},
            indent=2,
        )
        + "\r\n"
    ).encode("utf-8")


def _installed_bytes(*, packs: dict[str, object]) -> bytes:
    return (
        json.dumps({"schema_version": "1.0", "packs": packs}, indent=1) + "\n"
    ).encode("utf-8")


def _installed_record(digest: str) -> dict[str, object]:
    return {
        "1.0.0": {
            "archive_sha256": digest,
            "manifest_sha256": digest,
            "registry_receipt": {"legacy": True},
        }
    }


class KnowledgeStateMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.paths = PackPaths.from_root(Path(self.temp.name) / "user-state")
        self.paths.state.mkdir(parents=True)

    def test_migration_backs_up_state_and_only_deactivates_legacy_metadata(self):
        active_before = _active_bytes(
            packs={
                LEGACY_NANO: {"version": "1.0.0", "archive_sha256": SHA_A},
                CURRENT_NANO: {"version": "2.0.0", "archive_sha256": SHA_B},
            }
        )
        installed_before = _installed_bytes(
            packs={
                LEGACY_UNO: _installed_record(SHA_A),
                CURRENT_NANO: _installed_record(SHA_B),
            }
        )
        self.paths.active.write_bytes(active_before)
        self.paths.installed_metadata.write_bytes(installed_before)

        cache_receipt = self.paths.cache / "legacy-object.receipt.json"
        legacy_store = self.paths.store / LEGACY_NANO / "1.0.0" / "payload.bin"
        legacy_override = self.paths.overrides / LEGACY_UNO / "notes.md"
        for path, content in (
            (
                cache_receipt,
                b'{"pack_id":"chatmaker-board-arduino-nano-classic-wiki"}\n',
            ),
            (legacy_store, b"legacy store bytes\x00"),
            (legacy_override, b"my user override\r\n"),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        preserved_before = {
            cache_receipt: cache_receipt.read_bytes(),
            legacy_store: legacy_store.read_bytes(),
            legacy_override: legacy_override.read_bytes(),
        }

        result = migrate_legacy_knowledge_state(self.paths)

        self.assertTrue(result.changed)
        self.assertEqual(
            result.deactivated_pack_ids,
            (LEGACY_NANO, LEGACY_UNO),
        )
        self.assertEqual(
            (result.backup_dir / "active.json").read_bytes(), active_before
        )
        self.assertEqual(
            (result.backup_dir / "installed-packs.json").read_bytes(),
            installed_before,
        )
        active_after = json.loads(self.paths.active.read_text(encoding="utf-8"))
        self.assertEqual(active_after["generation"], 8)
        self.assertEqual(set(active_after["packs"]), {CURRENT_NANO})
        installed_after = json.loads(
            self.paths.installed_metadata.read_text(encoding="utf-8")
        )
        self.assertEqual(set(installed_after["packs"]), {CURRENT_NANO})
        self.assertEqual(
            set(result.preserved_paths),
            {
                self.paths.cache,
                self.paths.store / LEGACY_NANO,
                self.paths.overrides / LEGACY_UNO,
            },
        )
        for path, content in preserved_before.items():
            self.assertEqual(path.read_bytes(), content)
        self.assertTrue(
            (self.paths.state / "knowledge-state-migration-v1.json").is_file()
        )

    def test_migration_is_idempotent_after_a_successful_run(self):
        self.paths.active.write_bytes(
            _active_bytes(
                packs={LEGACY_NANO: {"version": "1.0.0", "archive_sha256": SHA_A}}
            )
        )

        first = migrate_legacy_knowledge_state(self.paths)
        migrated_bytes = self.paths.active.read_bytes()
        second = migrate_legacy_knowledge_state(self.paths)

        self.assertTrue(first.changed)
        self.assertFalse(second.changed)
        self.assertEqual(second.backup_dir, first.backup_dir)
        self.assertEqual(second.deactivated_pack_ids, first.deactivated_pack_ids)
        self.assertEqual(self.paths.active.read_bytes(), migrated_bytes)

    def test_migration_waits_for_the_pack_manager_lock(self):
        self.paths.active.write_bytes(
            _active_bytes(
                packs={LEGACY_NANO: {"version": "1.0.0", "archive_sha256": SHA_A}}
            )
        )
        executor = ThreadPoolExecutor(max_workers=1)
        self.addCleanup(executor.shutdown)

        with exclusive_file_lock(self.paths.manager_lock):
            future = executor.submit(migrate_legacy_knowledge_state, self.paths)
            with self.assertRaises(FutureTimeoutError):
                future.result(timeout=0.2)

        result = future.result(timeout=5)
        self.assertTrue(result.changed)

    def test_failure_before_replacement_leaves_original_state_bytes_unchanged(self):
        active_before = _active_bytes(
            packs={LEGACY_NANO: {"version": "1.0.0", "archive_sha256": SHA_A}}
        )
        installed_before = _installed_bytes(
            packs={LEGACY_UNO: _installed_record(SHA_B)}
        )
        self.paths.active.write_bytes(active_before)
        self.paths.installed_metadata.write_bytes(installed_before)
        observed_points: list[str] = []

        def fail(point: str) -> None:
            observed_points.append(point)
            if point == "knowledge_migration.before_state_replace":
                raise RuntimeError(point)

        with self.assertRaises(KnowledgeStateMigrationError):
            migrate_legacy_knowledge_state(self.paths, failure_injector=fail)

        self.assertIn("knowledge_migration.before_state_replace", observed_points)
        self.assertEqual(self.paths.active.read_bytes(), active_before)
        self.assertEqual(self.paths.installed_metadata.read_bytes(), installed_before)
        self.assertFalse(
            (self.paths.state / "knowledge-state-migration-v1.json").exists()
        )

    def test_unsafe_backup_parent_is_rejected_without_changing_state(self):
        active_before = _active_bytes(
            packs={LEGACY_NANO: {"version": "1.0.0", "archive_sha256": SHA_A}}
        )
        self.paths.active.write_bytes(active_before)
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        backup_link = self.paths.state / "backups"
        try:
            os.symlink(outside, backup_link, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            if os.name != "nt":
                self.skipTest(f"directory symlinks unavailable: {exc}")
            subprocess.run(
                ["cmd.exe", "/d", "/c", "mklink", "/J", str(backup_link), str(outside)],
                check=True,
                capture_output=True,
                text=True,
            )
            self.addCleanup(os.rmdir, backup_link)

        with self.assertRaises(KnowledgeStateMigrationError):
            migrate_legacy_knowledge_state(self.paths)

        self.assertEqual(self.paths.active.read_bytes(), active_before)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse(
            (self.paths.state / "knowledge-state-migration-v1.json").exists()
        )

    def test_migration_removes_only_exact_legacy_ids(self):
        self.paths.active.write_bytes(
            _active_bytes(
                packs={
                    LEGACY_NANO: {"version": "1.0.0", "archive_sha256": SHA_A},
                    UNKNOWN_PACK: {"version": "1.0.0", "archive_sha256": SHA_B},
                }
            )
        )

        migrate_legacy_knowledge_state(self.paths)

        active = json.loads(self.paths.active.read_text(encoding="utf-8"))
        self.assertNotIn(LEGACY_NANO, active["packs"])
        self.assertIn(UNKNOWN_PACK, active["packs"])

    def test_pack_manager_migrates_before_current_allowlist_validation(self):
        self.paths.active.write_bytes(
            _active_bytes(
                generation=3,
                packs={LEGACY_NANO: {"version": "1.0.0", "archive_sha256": SHA_A}},
            )
        )
        self.paths.installed_metadata.write_bytes(
            _installed_bytes(packs={LEGACY_UNO: _installed_record(SHA_B)})
        )
        manager = PackManager(
            user_root=self.paths.root,
            trust_store={
                "registry_url": "https://registry.example.invalid/registry.json",
                "signature_url": "https://registry.example.invalid/registry.sig.json",
                "keys": {},
            },
        )

        token = manager.generation_token()

        self.assertTrue(token.startswith("4:"), token)
        active = json.loads(self.paths.active.read_text(encoding="utf-8"))
        installed = json.loads(
            self.paths.installed_metadata.read_text(encoding="utf-8")
        )
        self.assertEqual(active["packs"], {})
        self.assertEqual(installed["packs"], {})


if __name__ == "__main__":
    unittest.main()
