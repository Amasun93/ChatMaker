from __future__ import annotations

from concurrent.futures import (
    ThreadPoolExecutor,
    TimeoutError as FutureTimeoutError,
)
from dataclasses import replace
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from runtime.chatmaker.installers import knowledge_state_migration as migration
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


def _create_junction(link: Path, target: Path) -> None:
    completed = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise OSError(completed.stderr or completed.stdout)


def _remove_junction(path: Path) -> None:
    if os.path.lexists(path):
        os.rmdir(path)


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
        self.assertTrue(
            os.path.samefile(second.backup_dir, first.backup_dir),
            (first.backup_dir, second.backup_dir),
        )
        self.assertEqual(second.deactivated_pack_ids, first.deactivated_pack_ids)
        self.assertEqual(self.paths.active.read_bytes(), migrated_bytes)

    def test_stale_marker_with_restored_legacy_state_is_not_trusted(self):
        active_before = _active_bytes(
            packs={LEGACY_NANO: {"version": "1.0.0", "archive_sha256": SHA_A}}
        )
        self.paths.active.write_bytes(active_before)
        first = migrate_legacy_knowledge_state(self.paths)
        self.paths.active.write_bytes(active_before)

        second = migrate_legacy_knowledge_state(self.paths)

        self.assertTrue(second.changed)
        self.assertNotEqual(second.backup_dir, first.backup_dir)
        active = json.loads(self.paths.active.read_text(encoding="utf-8"))
        self.assertNotIn(LEGACY_NANO, active["packs"])

    def test_preseeded_marker_with_missing_backup_cannot_skip_migration(self):
        self.paths.active.write_bytes(
            _active_bytes(
                packs={LEGACY_NANO: {"version": "1.0.0", "archive_sha256": SHA_A}}
            )
        )
        marker = {
            "schema_version": "1.0",
            "migration": "knowledge-pack-identity-v1",
            "backup_dir": "state/backups/knowledge-state-migration-v1/missing",
            "deactivated_pack_ids": [LEGACY_NANO],
            "preserved_paths": [],
        }
        (self.paths.state / "knowledge-state-migration-v1.json").write_text(
            json.dumps(marker), encoding="utf-8"
        )

        result = migrate_legacy_knowledge_state(self.paths)

        self.assertTrue(result.changed)
        self.assertTrue(result.backup_dir.is_dir())
        active = json.loads(self.paths.active.read_text(encoding="utf-8"))
        self.assertNotIn(LEGACY_NANO, active["packs"])

    @unittest.skipUnless(os.name == "nt", "Windows handle traversal only")
    def test_pack_manager_accepts_clean_state_when_marker_backup_was_deleted(self):
        self.paths.active.write_bytes(
            _active_bytes(
                packs={LEGACY_NANO: {"version": "1.0.0", "archive_sha256": SHA_A}}
            )
        )
        first = migrate_legacy_knowledge_state(self.paths)
        shutil.rmtree(first.backup_dir)
        active_before = self.paths.active.read_bytes()
        manager = PackManager(
            user_root=self.paths.root,
            trust_store={
                "registry_url": "https://registry.example.invalid/registry.json",
                "signature_url": "https://registry.example.invalid/registry.sig.json",
                "keys": {},
            },
        )

        token = manager.generation_token()

        self.assertTrue(token.startswith("8:"), token)
        self.assertEqual(self.paths.active.read_bytes(), active_before)

    def test_marker_paths_reject_windows_separators_drives_and_unc(self):
        for value in (
            r"state\..\outside",
            r"C:\outside",
            r"\\server\share\backup",
        ):
            with self.subTest(value=value):
                with self.assertRaises(KnowledgeStateMigrationError):
                    migration._path_from_marker(value, self.paths.root)

    @unittest.skipUnless(os.name == "nt", "Windows junction semantics only")
    def test_marker_backup_cannot_escape_root_through_intermediate_junction(self):
        self.paths.active.write_bytes(_active_bytes(packs={}))
        outside = Path(self.temp.name) / "outside-marker"
        run_id = "d" * 32
        external_backup = outside / "knowledge-state-migration-v1" / run_id
        external_backup.mkdir(parents=True)
        (external_backup / "active.json").write_bytes(
            _active_bytes(
                packs={LEGACY_NANO: {"version": "1.0.0", "archive_sha256": SHA_A}}
            )
        )
        backup_link = self.paths.state / "backups"
        _create_junction(backup_link, outside)
        self.addCleanup(_remove_junction, backup_link)
        marker = {
            "schema_version": "1.0",
            "migration": "knowledge-pack-identity-v1",
            "backup_dir": f"state/backups/knowledge-state-migration-v1/{run_id}",
            "deactivated_pack_ids": [LEGACY_NANO],
            "preserved_paths": [],
        }
        (self.paths.state / "knowledge-state-migration-v1.json").write_text(
            json.dumps(marker), encoding="utf-8"
        )

        result = migrate_legacy_knowledge_state(self.paths)

        self.assertIsNone(result.backup_dir)
        self.assertEqual(result.deactivated_pack_ids, ())

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

    def test_directory_sync_failure_after_state_replace_restores_original_bytes(self):
        active_before = _active_bytes(
            packs={LEGACY_NANO: {"version": "1.0.0", "archive_sha256": SHA_A}}
        )
        installed_before = _installed_bytes(
            packs={LEGACY_UNO: _installed_record(SHA_B)}
        )
        self.paths.active.write_bytes(active_before)
        self.paths.installed_metadata.write_bytes(installed_before)
        real_sync = migration._fsync_directory
        failed = False

        def fail_first_state_sync(path: Path, **kwargs: object) -> None:
            nonlocal failed
            if path == self.paths.state and not failed:
                failed = True
                raise OSError("injected state directory sync failure")
            real_sync(path, **kwargs)

        with mock.patch.object(
            migration, "_fsync_directory", side_effect=fail_first_state_sync
        ):
            with self.assertRaises(KnowledgeStateMigrationError):
                migrate_legacy_knowledge_state(self.paths)

        self.assertTrue(failed)
        self.assertEqual(self.paths.active.read_bytes(), active_before)
        self.assertEqual(self.paths.installed_metadata.read_bytes(), installed_before)
        self.assertFalse(
            (self.paths.state / "knowledge-state-migration-v1.json").exists()
        )

    def test_marker_sync_failure_removes_marker_and_restores_original_state(self):
        active_before = _active_bytes(
            packs={LEGACY_NANO: {"version": "1.0.0", "archive_sha256": SHA_A}}
        )
        self.paths.active.write_bytes(active_before)
        real_sync = migration._fsync_directory
        state_syncs = 0

        def fail_second_state_sync(path: Path, **kwargs: object) -> None:
            nonlocal state_syncs
            if path == self.paths.state:
                state_syncs += 1
                if state_syncs == 2:
                    raise OSError("injected marker directory sync failure")
            real_sync(path, **kwargs)

        with mock.patch.object(
            migration, "_fsync_directory", side_effect=fail_second_state_sync
        ):
            with self.assertRaises(KnowledgeStateMigrationError):
                migrate_legacy_knowledge_state(self.paths)

        self.assertGreaterEqual(state_syncs, 2)
        self.assertEqual(self.paths.active.read_bytes(), active_before)
        self.assertFalse(
            (self.paths.state / "knowledge-state-migration-v1.json").exists()
        )

    @unittest.skipUnless(os.name == "nt", "Windows directory flush semantics only")
    def test_windows_directory_sync_invokes_flush_file_buffers_adapter(self):
        calls: list[Path] = []

        migration._fsync_directory(
            self.paths.state,
            windows_flusher=calls.append,
        )

        self.assertEqual(calls, [self.paths.state])

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
            _create_junction(backup_link, outside)
            self.addCleanup(_remove_junction, backup_link)

        with self.assertRaises(KnowledgeStateMigrationError):
            migrate_legacy_knowledge_state(self.paths)

        self.assertEqual(self.paths.active.read_bytes(), active_before)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse(
            (self.paths.state / "knowledge-state-migration-v1.json").exists()
        )

    @unittest.skipUnless(os.name == "nt", "Windows junction semantics only")
    def test_backup_directory_is_guarded_against_in_place_junction_swap(self):
        self.paths.active.write_bytes(
            _active_bytes(
                packs={LEGACY_NANO: {"version": "1.0.0", "archive_sha256": SHA_A}}
            )
        )
        outside = Path(self.temp.name) / "outside-swap"
        outside.mkdir()
        displaced = Path(self.temp.name) / "displaced-backup"
        attempted = False
        blocked_error: OSError | None = None
        swapped: Path | None = None

        def attempt_swap(point: str) -> None:
            nonlocal attempted, blocked_error, swapped
            if point != "knowledge_migration.before_first_backup_write":
                return
            candidates = list(
                (
                    self.paths.state
                    / "backups"
                    / "knowledge-state-migration-v1"
                ).iterdir()
            )
            self.assertEqual(len(candidates), 1)
            swapped = candidates[0]
            attempted = True
            try:
                os.replace(swapped, displaced)
                _create_junction(swapped, outside)
            except OSError as exc:
                blocked_error = exc

        try:
            result = migrate_legacy_knowledge_state(
                self.paths, failure_injector=attempt_swap
            )
        finally:
            if swapped is not None and migration.is_reparse(swapped):
                _remove_junction(swapped)
            if displaced.exists() and swapped is not None and not swapped.exists():
                os.replace(displaced, swapped)

        self.assertTrue(result.changed)
        self.assertTrue(attempted)
        self.assertIsNotNone(blocked_error)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertTrue((result.backup_dir / "active.json").is_file())

    def _assert_windows_intermediate_swap_is_handle_relative(
        self,
        point: str,
        *,
        require_swap: bool = False,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            base = Path(temp_name) / "base"
            paths = PackPaths.from_root(base / "user")
            paths.state.mkdir(parents=True)
            active_before = _active_bytes(
                packs={
                    LEGACY_NANO: {
                        "version": "1.0.0",
                        "archive_sha256": SHA_A,
                    }
                }
            )
            paths.active.write_bytes(active_before)
            outside = Path(temp_name) / "outside-state"
            outside.mkdir()
            outside_active = _active_bytes(packs={}, generation=99)
            (outside / "active.json").write_bytes(outside_active)
            displaced = Path(temp_name) / "displaced-state"
            attempted = False
            swapped = False
            blocked_error: OSError | None = None

            def swap_state(observed: str) -> None:
                nonlocal attempted, blocked_error, swapped
                if observed != point:
                    return
                attempted = True
                try:
                    os.replace(paths.state, displaced)
                    _create_junction(paths.state, outside)
                    swapped = True
                except OSError as exc:
                    blocked_error = exc

            try:
                result = migrate_legacy_knowledge_state(
                    paths,
                    failure_injector=swap_state,
                )
            finally:
                if swapped and migration.is_reparse(paths.state):
                    _remove_junction(paths.state)
                if displaced.exists() and not paths.state.exists():
                    os.replace(displaced, paths.state)

            self.assertTrue(attempted)
            self.assertTrue(swapped or blocked_error is not None)
            if require_swap:
                self.assertTrue(swapped)
            self.assertTrue(result.changed)
            migrated = json.loads(paths.active.read_text(encoding="utf-8"))
            self.assertNotIn(LEGACY_NANO, migrated["packs"])
            self.assertEqual((outside / "active.json").read_bytes(), outside_active)
            self.assertEqual(sorted(path.name for path in outside.iterdir()), ["active.json"])

    @unittest.skipUnless(os.name == "nt", "Windows junction semantics only")
    def test_windows_state_read_survives_intermediate_junction_swap(self):
        self._assert_windows_intermediate_swap_is_handle_relative(
            "knowledge_migration.before_state_read",
            require_swap=True,
        )

    @unittest.skipUnless(os.name == "nt", "Windows junction semantics only")
    def test_windows_backup_temp_create_survives_intermediate_junction_swap(self):
        self._assert_windows_intermediate_swap_is_handle_relative(
            "knowledge_migration.before_backup_temp_create"
        )

    @unittest.skipUnless(os.name == "nt", "Windows junction semantics only")
    def test_windows_state_rename_survives_intermediate_junction_swap(self):
        self._assert_windows_intermediate_swap_is_handle_relative(
            "knowledge_migration.before_state_rename"
        )

    def test_pack_manager_migrates_relative_user_root_from_current_directory(self):
        with tempfile.TemporaryDirectory() as temp_name:
            previous = Path.cwd()
            os.chdir(temp_name)
            try:
                paths = PackPaths.from_root(Path("relative-user"))
                paths.state.mkdir(parents=True)
                paths.active.write_bytes(
                    _active_bytes(
                        packs={
                            LEGACY_NANO: {
                                "version": "1.0.0",
                                "archive_sha256": SHA_A,
                            }
                        }
                    )
                )

                manager = PackManager(
                    user_root=Path("relative-user"),
                    trust_store={
                        "registry_url": "https://registry.example.invalid/registry.json",
                        "signature_url": "https://registry.example.invalid/registry.sig.json",
                        "keys": {},
                    },
                )

                token = manager.generation_token()

                self.assertTrue(token.startswith("8:"), token)
                active = json.loads(paths.active.read_text(encoding="utf-8"))
                self.assertNotIn(LEGACY_NANO, active["packs"])
            finally:
                os.chdir(previous)

    @unittest.skipUnless(os.name == "nt", "Windows NT path contract only")
    def test_windows_nt_path_conversion_supports_dos_and_unc_roots(self):
        self.assertEqual(
            migration._windows_nt_path(Path(r"C:\Users\maker\state")),
            r"\??\C:\Users\maker\state",
        )
        self.assertEqual(
            migration._windows_nt_path(Path(r"\\server\share\state")),
            r"\??\UNC\server\share\state",
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

    def test_malicious_pack_paths_are_rejected_before_lock_or_backup_write(self):
        outside_state = Path(self.temp.name) / "outside-state"
        outside_state.mkdir()
        outside_active = outside_state / "active.json"
        active_before = _active_bytes(
            packs={LEGACY_NANO: {"version": "1.0.0", "archive_sha256": SHA_A}}
        )
        outside_active.write_bytes(active_before)
        malicious = replace(
            self.paths,
            state=outside_state,
            active=outside_active,
            installed_metadata=outside_state / "installed-packs.json",
        )

        with self.assertRaises(KnowledgeStateMigrationError):
            migrate_legacy_knowledge_state(malicious)

        self.assertFalse(self.paths.manager_lock.exists())
        self.assertEqual(outside_active.read_bytes(), active_before)
        self.assertFalse((outside_state / "backups").exists())

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
