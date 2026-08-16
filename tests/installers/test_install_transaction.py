from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.installers import codex, transaction as transaction_module, workbuddy  # noqa: E402
from chatmaker.installers.transaction import (  # noqa: E402
    InstallConflict,
    InstallTransaction,
    UnsafeInstallPath,
    _path_hash,
)


class InstallTransactionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.management_root = self.root / "user" / ".chatmaker"
        self.skills_root = self.root / "host" / "skills"
        self.config = self.root / "host" / "mcp.json"
        self.source = self.root / "source"
        self._write_source("v1")

    def _write_source(self, marker: str) -> None:
        for name in ("chatmaker", "chatduino", "chatweb"):
            skill = self.source / name
            skill.mkdir(parents=True, exist_ok=True)
            (skill / "SKILL.md").write_text(
                f"---\nname: {name}\n---\n{marker}\n", encoding="utf-8"
            )

    def _changes(self):
        return [
            {
                "kind": "skill_bundle",
                "source": self.source,
                "path": self.skills_root,
                "names": ["chatmaker", "chatduino", "chatweb"],
            },
            {
                "kind": "mcp_server",
                "path": self.config,
                "server_key": "chatmaker-test",
                "server": {"type": "stdio", "command": "python", "args": ["-m", "test"]},
            },
        ]

    def _transaction(self, *, fail_at: str | None = None) -> InstallTransaction:
        def inject(point, _context):
            if point == fail_at:
                raise RuntimeError(f"injected {point} failure")

        return InstallTransaction(
            root=self.management_root,
            installation_id="test-install",
            failure_injector=inject if fail_at else None,
        )

    def _seed_existing_state(self) -> None:
        old = self.skills_root / "chatmaker"
        old.mkdir(parents=True)
        (old / "old.txt").write_text("original skill", encoding="utf-8")
        self.config.parent.mkdir(parents=True, exist_ok=True)
        self.config.write_text(
            json.dumps(
                {
                    "theme": "dark",
                    "mcpServers": {
                        "chatmaker-test": {"command": "old"},
                        "unrelated": {"command": "keep"},
                    },
                }
            ),
            encoding="utf-8",
        )

    def _assert_original_state(self) -> None:
        self.assertEqual(
            (self.skills_root / "chatmaker" / "old.txt").read_text(encoding="utf-8"),
            "original skill",
        )
        self.assertFalse((self.skills_root / "chatduino").exists())
        self.assertFalse((self.skills_root / "chatweb").exists())
        saved = json.loads(self.config.read_text(encoding="utf-8"))
        self.assertEqual(saved["theme"], "dark")
        self.assertEqual(saved["mcpServers"]["chatmaker-test"], {"command": "old"})
        self.assertEqual(saved["mcpServers"]["unrelated"], {"command": "keep"})

    @staticmethod
    def _crash_at(expected_point):
        class SimulatedProcessExit(BaseException):
            pass

        def inject(point, _context):
            if point == expected_point:
                raise SimulatedProcessExit(point)

        return SimulatedProcessExit, inject

    def test_prepared_apply_is_rolled_back_by_the_next_locked_entrypoint(self):
        self._seed_existing_state()
        crash, inject = self._crash_at("verification")
        transaction = InstallTransaction(
            root=self.management_root,
            installation_id="test-install",
            failure_injector=inject,
        )

        with self.assertRaises(crash):
            transaction.apply(self._changes())

        recovered = self._transaction().uninstall()

        self.assertEqual(recovered.status, "already_absent")
        self._assert_original_state()
        journals = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in (self.management_root / "transactions").glob("*.json")
        ]
        self.assertEqual([item["status"] for item in journals], ["rolled_back"])

    def test_committed_apply_is_rolled_forward_before_repeat_install(self):
        crash, inject = self._crash_at("state_replacement")
        transaction = InstallTransaction(
            root=self.management_root,
            installation_id="test-install",
            failure_injector=inject,
        )

        with self.assertRaises(crash):
            transaction.apply(self._changes())
        journals_before = sorted((self.management_root / "transactions").glob("*.json"))
        backups_before = sorted((self.management_root / "backups").glob("**/*"))

        recovered = self._transaction().apply(self._changes())

        self.assertEqual(recovered.status, "already_current")
        self.assertEqual(sorted((self.management_root / "transactions").glob("*.json")), journals_before)
        self.assertEqual(sorted((self.management_root / "backups").glob("**/*")), backups_before)

    def test_unbound_prepared_journal_is_retired_without_trusting_its_records(self):
        crash, inject = self._crash_at("pending_state_replacement")
        transaction = InstallTransaction(
            root=self.management_root,
            installation_id="test-install",
            failure_injector=inject,
        )

        with self.assertRaises(crash):
            transaction.apply(self._changes())
        journal_path = next((self.management_root / "transactions").glob("*.json"))
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        journal["records"][0]["target"] = str(self.root / "must-not-touch")
        journal_path.write_text(json.dumps(journal), encoding="utf-8")

        result = self._transaction().uninstall()

        self.assertEqual(result.status, "already_absent")
        self.assertFalse((self.root / "must-not-touch").exists())
        retired = json.loads(journal_path.read_text(encoding="utf-8"))
        self.assertEqual(retired["status"], "rolled_back")
        self.assertEqual(retired["recovery"], "unbound_before_mutation")

    def test_restore_crash_is_resumed_idempotently_by_next_restore(self):
        self._seed_existing_state()
        installed = self._transaction().apply(self._changes())
        crash, inject = self._crash_at("restore_after_target")
        crashing = InstallTransaction(
            root=self.management_root,
            installation_id="test-install",
            failure_injector=inject,
        )

        with self.assertRaises(crash):
            crashing.restore(installed.transaction_id)

        recovered = self._transaction().restore(installed.transaction_id)

        self.assertEqual(recovered.status, "restored")
        self._assert_original_state()
        repeated = self._transaction().restore(installed.transaction_id)
        self.assertEqual(repeated.status, "already_restored")

    def test_committed_restore_rolls_forward_state_on_next_entrypoint(self):
        self._seed_existing_state()
        installed = self._transaction().apply(self._changes())
        crash, inject = self._crash_at("restore_state_replacement")
        crashing = InstallTransaction(
            root=self.management_root,
            installation_id="test-install",
            failure_injector=inject,
        )

        with self.assertRaises(crash):
            crashing.restore(installed.transaction_id)

        recovered = self._transaction().restore(installed.transaction_id)

        self.assertEqual(recovered.status, "already_restored")
        self._assert_original_state()

    def test_uninstall_crash_is_resumed_idempotently_by_next_uninstall(self):
        self._seed_existing_state()
        self._transaction().apply(self._changes())
        crash, inject = self._crash_at("uninstall_after_target")
        crashing = InstallTransaction(
            root=self.management_root,
            installation_id="test-install",
            failure_injector=inject,
        )

        with self.assertRaises(crash):
            crashing.uninstall()

        recovered = self._transaction().uninstall()

        self.assertEqual(recovered.status, "uninstalled")
        self._assert_original_state()
        self.assertEqual(self._transaction().uninstall().status, "already_absent")

    def test_finalized_uninstall_removes_recovery_tombstone_on_next_entrypoint(self):
        self._seed_existing_state()
        self._transaction().apply(self._changes())
        crash, inject = self._crash_at("uninstall_journal_finalization")
        crashing = InstallTransaction(
            root=self.management_root,
            installation_id="test-install",
            failure_injector=inject,
        )

        with self.assertRaises(crash):
            crashing.uninstall()
        self.assertEqual(len(list((self.management_root / "state").glob("*.json"))), 1)

        recovered = self._transaction().uninstall()

        self.assertEqual(recovered.status, "already_absent")
        self._assert_original_state()
        self.assertEqual(list((self.management_root / "state").glob("*.json")), [])

    def test_active_state_binding_rejects_a_tampered_committed_journal(self):
        self._seed_existing_state()
        installed = self._transaction().apply(self._changes())
        outside = self.root / "outside-managed"
        shutil_source = self.skills_root / "chatmaker"
        import shutil

        shutil.copytree(shutil_source, outside)
        outside_before = {
            path.relative_to(outside).as_posix(): path.read_bytes()
            for path in outside.rglob("*")
            if path.is_file()
        }
        journal_path = Path(installed["manifest"])
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        record = next(item for item in journal["records"] if item["name"] == "chatmaker")
        record["target"] = str(outside)
        record["identity"] = f"skill:{outside}"
        journal_path.write_text(json.dumps(journal), encoding="utf-8")

        with self.assertRaises(InstallConflict):
            self._transaction().restore(installed.transaction_id)

        self.assertEqual(
            {
                path.relative_to(outside).as_posix(): path.read_bytes()
                for path in outside.rglob("*")
                if path.is_file()
            },
            outside_before,
        )
        self.assertTrue((self.skills_root / "chatmaker" / "SKILL.md").is_file())

    def test_active_state_binding_rejects_tampered_restore_state_fields(self):
        self._seed_existing_state()
        installed = self._transaction().apply(self._changes())
        journal_path = Path(installed["manifest"])
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        journal["previous_state"] = {
            "schema_version": "1.0",
            "installation_id": "attacker",
            "managed": [],
        }
        journal_path.write_text(json.dumps(journal), encoding="utf-8")

        with self.assertRaises(InstallConflict):
            self._transaction().restore(installed.transaction_id)

        self.assertTrue((self.skills_root / "chatmaker" / "SKILL.md").is_file())

    def test_partial_windows_copy_fallback_restores_displaced_original(self):
        self._seed_existing_state()
        real_replace = transaction_module.os.replace
        real_copytree = transaction_module.shutil.copytree

        def force_copy_fallback(source, target, *args, **kwargs):
            if Path(source).name.endswith(".staging") and Path(target).name == "chatmaker":
                raise PermissionError("force Windows copy fallback")
            return real_replace(source, target, *args, **kwargs)

        def fail_after_partial_copy(source, target, *args, **kwargs):
            if Path(source).name.endswith(".staging") and Path(target).name == "chatmaker":
                Path(target).mkdir(parents=True)
                (Path(target) / "partial.txt").write_text("partial", encoding="utf-8")
                raise OSError("copy interrupted")
            return real_copytree(source, target, *args, **kwargs)

        with mock.patch.object(transaction_module.os, "replace", side_effect=force_copy_fallback), mock.patch.object(
            transaction_module.shutil, "copytree", side_effect=fail_after_partial_copy
        ):
            with self.assertRaisesRegex(OSError, "copy interrupted"):
                self._transaction().apply(self._changes())

        self._assert_original_state()
        self.assertFalse((self.skills_root / "chatmaker" / "partial.txt").exists())

    def test_restore_preflights_every_update_backup_before_mutating_any_target(self):
        self._seed_existing_state()
        transaction = self._transaction()
        transaction.apply(self._changes())
        self._write_source("v2")
        updated = transaction.apply(self._changes())
        installed_bytes = {
            name: (self.skills_root / name / "SKILL.md").read_bytes()
            for name in ("chatmaker", "chatduino", "chatweb")
        }
        journal = json.loads(Path(updated["manifest"]).read_text(encoding="utf-8"))
        late_record = next(item for item in journal["records"] if item["name"] == "chatmaker")
        import shutil

        shutil.rmtree(late_record["backup"])

        with self.assertRaises((InstallConflict, FileNotFoundError)):
            transaction.restore(updated.transaction_id)

        self.assertEqual(
            {
                name: (self.skills_root / name / "SKILL.md").read_bytes()
                for name in installed_bytes
            },
            installed_bytes,
        )

    def test_restore_validates_before_hash_before_using_backup(self):
        self._seed_existing_state()
        transaction = self._transaction()
        transaction.apply(self._changes())
        self._write_source("v2")
        updated = transaction.apply(self._changes())
        journal = json.loads(Path(updated["manifest"]).read_text(encoding="utf-8"))
        record = next(item for item in journal["records"] if item["name"] == "chatmaker")
        (Path(record["backup"]) / "SKILL.md").write_text("tampered backup", encoding="utf-8")
        installed_before = (self.skills_root / "chatmaker" / "SKILL.md").read_bytes()

        with self.assertRaises(InstallConflict):
            transaction.restore(updated.transaction_id)

        self.assertEqual(
            (self.skills_root / "chatmaker" / "SKILL.md").read_bytes(),
            installed_before,
        )

    def test_uninstall_preflights_original_baselines_before_any_mutation(self):
        self._seed_existing_state()
        transaction = self._transaction()
        transaction.apply(self._changes())
        self._write_source("v2")
        transaction.apply(self._changes())
        state_path = next((self.management_root / "state").glob("*.json"))
        state = json.loads(state_path.read_text(encoding="utf-8"))
        baseline = next(
            item["baseline"]
            for item in state["managed"]
            if item["name"] == "chatmaker"
        )
        (Path(baseline["backup"]) / "old.txt").write_text(
            "tampered baseline", encoding="utf-8"
        )
        installed_before = {
            name: (self.skills_root / name / "SKILL.md").read_bytes()
            for name in ("chatmaker", "chatduino", "chatweb")
        }

        with self.assertRaises(InstallConflict):
            transaction.uninstall()

        self.assertEqual(
            {
                name: (self.skills_root / name / "SKILL.md").read_bytes()
                for name in installed_before
            },
            installed_before,
        )

    def test_cleanup_failure_cannot_leave_active_state_claiming_rolled_back_targets(self):
        self._seed_existing_state()
        real_remove = transaction_module._remove_path
        failed = False

        def reject_displaced_cleanup(path):
            nonlocal failed
            if not failed and Path(path).name.endswith(".displaced"):
                failed = True
                raise OSError("cleanup failed")
            return real_remove(path)

        with mock.patch.object(transaction_module, "_remove_path", side_effect=reject_displaced_cleanup):
            with self.assertRaisesRegex(OSError, "cleanup failed"):
                self._transaction().apply(self._changes())

        self._assert_original_state()
        self.assertEqual(list((self.management_root / "state").glob("*.json")), [])

    def test_skill_hash_frames_file_boundaries_and_structure(self):
        packed = self.root / "packed"
        split = self.root / "split"
        packed.mkdir()
        split.mkdir()
        (packed / "a").write_bytes(b"X\0f\0b\0Y")
        (split / "a").write_bytes(b"X")
        (split / "b").write_bytes(b"Y")

        self.assertNotEqual(_path_hash(packed), _path_hash(split))

    def test_codex_and_workbuddy_wrappers_share_one_injected_global_root(self):
        global_root = self.root / "global" / ".chatmaker"
        codex_home = self.root / ".codex"
        workbuddy_config = self.root / ".workbuddy" / "mcp.json"

        codex.install(codex_home, source_skills=ROOT / "skills", transaction_root=global_root)
        workbuddy.install(
            workbuddy_config,
            python_executable="python",
            source_skills=ROOT / "skills",
            transaction_root=global_root,
        )

        self.assertEqual(len(list((global_root / "state").glob("*.json"))), 2)
        self.assertTrue((global_root / "locks" / "install.lock").is_file())
        self.assertFalse((codex_home / ".chatmaker").exists())
        self.assertFalse((workbuddy_config.parent / ".chatmaker").exists())

    def test_public_wrappers_reject_relative_target_paths(self):
        with self.assertRaises(UnsafeInstallPath):
            codex.install(
                Path("relative-codex-home"),
                source_skills=ROOT / "skills",
                transaction_root=self.management_root,
            )
        with self.assertRaises(UnsafeInstallPath):
            workbuddy.install(
                Path("relative-workbuddy/mcp.json"),
                source_skills=ROOT / "skills",
                transaction_root=self.management_root,
            )
        with self.assertRaises(UnsafeInstallPath):
            codex.doctor(Path("relative-codex-home"))
        with self.assertRaises(UnsafeInstallPath):
            workbuddy.doctor(Path("relative-workbuddy/mcp.json"))

    @unittest.skipUnless(os.name == "nt", "Windows path aliases only")
    def test_windows_case_and_extended_aliases_share_one_managed_identity(self):
        config = self.root / "MixedCase" / "Mcp.json"
        changes = [
            {
                "kind": "mcp_server",
                "path": config,
                "server_key": "chatmaker-test",
                "server": {"command": "python"},
            }
        ]
        transaction = self._transaction()
        first = transaction.apply(changes)
        case_alias = Path(str(config).swapcase())
        extended_alias = Path("\\\\?\\" + str(config))

        second = transaction.apply([{**changes[0], "path": case_alias}])
        third = transaction.apply([{**changes[0], "path": extended_alias}])

        self.assertEqual(first.transaction_id, second.transaction_id)
        self.assertEqual(second.status, "already_current")
        self.assertEqual(third.status, "already_current")

    @unittest.skipUnless(os.name == "nt", "Windows DOS alias only")
    def test_windows_dos_alias_maps_to_the_same_managed_identity(self):
        directory = self.root / "Long Directory Name"
        directory.mkdir()
        config = directory / "Long Config Name.json"
        changes = [
            {
                "kind": "mcp_server",
                "path": config,
                "server_key": "chatmaker-test",
                "server": {"command": "python"},
            }
        ]
        transaction = self._transaction()
        first = transaction.apply(changes)
        buffer = transaction_module.ctypes.create_unicode_buffer(32768)
        written = transaction_module.ctypes.windll.kernel32.GetShortPathNameW(
            str(config), buffer, len(buffer)
        )
        if not written or written >= len(buffer) or buffer.value == str(config):
            self.skipTest("DOS 8.3 alias is unavailable on this volume")

        second = transaction.apply([{**changes[0], "path": Path(buffer.value)}])

        self.assertEqual(second.status, "already_current")
        self.assertEqual(second.transaction_id, first.transaction_id)

    @unittest.skipUnless(os.name == "nt", "Windows UNC policy only")
    def test_unc_transaction_root_is_rejected_as_unsupported(self):
        with self.assertRaisesRegex(UnsafeInstallPath, "network|UNC"):
            InstallTransaction(root=Path(r"\\server\share\.chatmaker"))

    @unittest.skipUnless(os.name == "nt", "Windows junction race only")
    def test_junction_swap_during_activation_never_writes_outside_target(self):
        self._seed_existing_state()
        outside = self.root / "outside-swap"
        outside.mkdir()
        displaced = self.root / "displaced-skills"
        swapped = False

        def swap_parent(point, context):
            nonlocal swapped
            if point != "skill_activation" or swapped:
                return
            os.replace(self.skills_root, displaced)
            completed = subprocess.run(
                ["cmd.exe", "/d", "/c", "mklink", "/J", str(self.skills_root), str(outside)],
                text=True,
                capture_output=True,
                check=False,
            )
            if completed.returncode != 0:
                os.replace(displaced, self.skills_root)
                return
            swapped = True

        transaction = InstallTransaction(
            root=self.management_root,
            installation_id="test-install",
            failure_injector=swap_parent,
        )
        try:
            with self.assertRaises((UnsafeInstallPath, InstallConflict, OSError)):
                transaction.apply(self._changes())
            self.assertEqual(list(outside.iterdir()), [])
        finally:
            if swapped and transaction_module.is_reparse(self.skills_root):
                os.rmdir(self.skills_root)
            if displaced.exists() and not self.skills_root.exists():
                os.replace(displaced, self.skills_root)

    def test_atomic_replacements_sync_their_parent_directories(self):
        self._seed_existing_state()
        synced = []
        real_sync = getattr(transaction_module, "_fsync_directory", None)
        if real_sync is None:
            self.fail("transaction has no directory durability primitive")

        def record_sync(path, *args, **kwargs):
            synced.append(Path(path))
            return real_sync(path, *args, **kwargs)

        with mock.patch.object(transaction_module, "_fsync_directory", side_effect=record_sync):
            installed = self._transaction().apply(self._changes())

        self.assertEqual(installed.status, "installed")
        self.assertIn(self.management_root / "transactions", synced)
        self.assertIn(self.management_root / "state", synced)
        self.assertIn(self.management_root / "backups" / installed.transaction_id, synced)

    def test_staging_failure_leaves_targets_and_active_state_untouched(self):
        self._seed_existing_state()

        with self.assertRaisesRegex(RuntimeError, "injected staging failure"):
            self._transaction(fail_at="staging").apply(self._changes())

        self._assert_original_state()
        self.assertEqual(list((self.management_root / "state").glob("*.json")), [])
        self.assertEqual(list((self.management_root / "backups").glob("*")), [])

    def test_missing_skill_entrypoint_is_rejected_before_any_install_write(self):
        (self.source / "chatweb" / "SKILL.md").unlink()

        with self.assertRaisesRegex(FileNotFoundError, "missing source Skill"):
            self._transaction().apply(self._changes())

        self.assertFalse(self.skills_root.exists())
        self.assertFalse(self.management_root.exists())

    def test_skill_activation_failure_compensates_every_activated_skill(self):
        self._seed_existing_state()

        def fail_on_second_skill(point, context):
            if point == "skill_activation" and context["identity"].endswith("chatduino"):
                raise RuntimeError("injected skill_activation failure")

        with self.assertRaisesRegex(RuntimeError, "injected skill_activation failure"):
            InstallTransaction(
                root=self.management_root,
                installation_id="test-install",
                failure_injector=fail_on_second_skill,
            ).apply(self._changes())

        self._assert_original_state()
        self.assertEqual(list((self.management_root / "state").glob("*.json")), [])

    def test_mcp_replacement_failure_restores_activated_skills_and_config(self):
        self._seed_existing_state()

        with self.assertRaisesRegex(RuntimeError, "injected mcp_replacement failure"):
            self._transaction(fail_at="mcp_replacement").apply(self._changes())

        self._assert_original_state()
        self.assertEqual(list((self.management_root / "state").glob("*.json")), [])

    def test_journal_replacement_failure_restores_all_user_files(self):
        self._seed_existing_state()

        with self.assertRaisesRegex(RuntimeError, "injected journal_replacement failure"):
            self._transaction(fail_at="journal_replacement").apply(self._changes())

        self._assert_original_state()
        self.assertEqual(list((self.management_root / "state").glob("*.json")), [])

    def test_verification_failure_restores_all_user_files(self):
        self._seed_existing_state()

        with self.assertRaisesRegex(RuntimeError, "injected verification failure"):
            self._transaction(fail_at="verification").apply(self._changes())

        self._assert_original_state()
        self.assertEqual(list((self.management_root / "state").glob("*.json")), [])

    def test_second_identical_apply_is_already_current_without_new_backup_or_hash(self):
        transaction = self._transaction()
        first = transaction.apply(self._changes())
        backups_before = sorted(path.relative_to(self.management_root) for path in self.management_root.glob("backups/**/*"))
        journals_before = sorted((self.management_root / "transactions").glob("*.json"))

        second = transaction.apply(self._changes())

        self.assertEqual(first.status, "installed")
        self.assertEqual(second.status, "already_current")
        self.assertEqual(second.transaction_id, first.transaction_id)
        self.assertEqual(second.managed_hash, first.managed_hash)
        self.assertEqual(
            sorted(path.relative_to(self.management_root) for path in self.management_root.glob("backups/**/*")),
            backups_before,
        )
        self.assertEqual(sorted((self.management_root / "transactions").glob("*.json")), journals_before)

    def test_update_keeps_first_preinstall_restore_point_for_uninstall(self):
        self._seed_existing_state()
        transaction = self._transaction()
        first = transaction.apply(self._changes())
        self._write_source("v2")

        updated = transaction.apply(self._changes())
        removed = transaction.uninstall()

        self.assertEqual(first.status, "installed")
        self.assertEqual(updated.status, "updated")
        self.assertNotEqual(updated.transaction_id, first.transaction_id)
        self.assertEqual(removed.status, "uninstalled")
        self._assert_original_state()

    def test_restore_uses_full_before_images_and_is_idempotent(self):
        self._seed_existing_state()
        transaction = self._transaction()
        installed = transaction.apply(self._changes())

        restored = transaction.restore(installed.transaction_id)
        repeated = transaction.restore(installed.transaction_id)

        self.assertEqual(restored.status, "restored")
        self.assertEqual(repeated.status, "already_restored")
        self._assert_original_state()

    def test_uninstall_is_idempotent(self):
        transaction = self._transaction()
        transaction.apply(self._changes())

        first = transaction.uninstall()
        second = transaction.uninstall()

        self.assertEqual(first.status, "uninstalled")
        self.assertEqual(second.status, "already_absent")
        self.assertFalse(self.config.exists())
        self.assertEqual(list(self.skills_root.iterdir()), [])

    def test_uninstall_reports_conflict_without_overwriting_modified_skill(self):
        transaction = self._transaction()
        transaction.apply(self._changes())
        changed = self.skills_root / "chatmaker" / "SKILL.md"
        changed.write_text("user edit", encoding="utf-8")

        result = transaction.uninstall()

        self.assertFalse(result.success)
        self.assertEqual(result.status, "conflict")
        self.assertIn("chatmaker", " ".join(item["identity"] for item in result.conflicts))
        self.assertEqual(changed.read_text(encoding="utf-8"), "user edit")
        self.assertTrue((self.skills_root / "chatduino" / "SKILL.md").is_file())

    def test_uninstall_reports_conflict_when_managed_mcp_entry_was_modified(self):
        transaction = self._transaction()
        transaction.apply(self._changes())
        config = json.loads(self.config.read_text(encoding="utf-8"))
        config["mcpServers"]["chatmaker-test"] = {"command": "user replacement"}
        self.config.write_text(json.dumps(config), encoding="utf-8")

        result = transaction.uninstall()

        self.assertFalse(result.success)
        self.assertEqual(result.status, "conflict")
        self.assertEqual(
            json.loads(self.config.read_text(encoding="utf-8"))["mcpServers"]["chatmaker-test"],
            {"command": "user replacement"},
        )

    def test_workbuddy_second_install_and_uninstall_preserve_later_user_server(self):
        home = self.root / ".workbuddy"
        config = home / "mcp.json"
        config.parent.mkdir(parents=True)
        config.write_text(
            json.dumps({"mcpServers": {"before": {"command": "keep-before"}}}),
            encoding="utf-8",
        )
        transaction_root = self.root / "global-workbuddy-state"
        first = workbuddy.install(
            config,
            python_executable="python",
            source_skills=ROOT / "skills",
            transaction_root=transaction_root,
        )
        backups_before = sorted((transaction_root / "backups").glob("**/*"))

        second = workbuddy.install(
            config,
            python_executable="python",
            source_skills=ROOT / "skills",
            transaction_root=transaction_root,
        )
        backups_after_second_install = sorted(
            (transaction_root / "backups").glob("**/*")
        )
        saved = json.loads(config.read_text(encoding="utf-8"))
        saved["mcpServers"]["later"] = {"command": "keep-later"}
        config.write_text(json.dumps(saved), encoding="utf-8")
        removed = workbuddy.uninstall(config, transaction_root=transaction_root)
        final = json.loads(config.read_text(encoding="utf-8"))

        self.assertEqual(first["status"], "installed")
        self.assertEqual(second["status"], "already_current")
        self.assertEqual(backups_after_second_install, backups_before)
        self.assertTrue(removed["success"])
        self.assertEqual(final["mcpServers"]["before"], {"command": "keep-before"})
        self.assertEqual(final["mcpServers"]["later"], {"command": "keep-later"})
        self.assertNotIn(workbuddy.SERVER_KEY, final["mcpServers"])

    def test_rejects_skill_name_traversal_before_writing_outside_target(self):
        outside = self.root / "host" / "escape"
        changes = [
            {
                "kind": "skill_bundle",
                "source": self.source,
                "path": self.skills_root,
                "names": ["../escape"],
            }
        ]

        with self.assertRaises(UnsafeInstallPath):
            self._transaction().apply(changes)

        self.assertFalse(outside.exists())
        self.assertFalse(self.management_root.exists())

    def test_mcp_key_cannot_escape_internal_staging_or_backup_paths(self):
        self.config.parent.mkdir(parents=True)
        self.config.write_text(
            json.dumps({"mcpServers": {"keep": {"command": "other"}}}),
            encoding="utf-8",
        )
        key = "/../../escaped"
        changes = [
            {
                "kind": "mcp_server",
                "path": self.config,
                "server_key": key,
                "server": {"command": "python"},
            }
        ]

        outside_seen_during_activation = []

        def inspect_then_fail(point, _context):
            if point == "mcp_replacement":
                outside_seen_during_activation.extend(self.root.glob("escaped*"))
                raise RuntimeError("stop after staging and backup")

        with self.assertRaisesRegex(RuntimeError, "stop after staging and backup"):
            InstallTransaction(
                root=self.management_root,
                installation_id="test-install",
                failure_injector=inspect_then_fail,
            ).apply(changes)

        self.assertEqual(outside_seen_during_activation, [])
        self.assertFalse((self.management_root / "backups" / "escaped").exists())
        self.assertEqual(
            json.loads(self.config.read_text(encoding="utf-8")),
            {"mcpServers": {"keep": {"command": "other"}}},
        )

    def test_rejects_symlinked_target_parent_without_touching_link_destination(self):
        outside = self.root / "outside"
        outside.mkdir()
        linked = self.root / "linked-skills"
        if os.name == "nt":
            completed = subprocess.run(
                ["cmd.exe", "/d", "/c", "mklink", "/J", str(linked), str(outside)],
                text=True,
                capture_output=True,
                check=False,
            )
            if completed.returncode != 0:
                self.skipTest(completed.stderr or completed.stdout)
            self.addCleanup(lambda: os.path.lexists(linked) and os.rmdir(linked))
        else:
            os.symlink(outside, linked, target_is_directory=True)
        changes = [
            {
                "kind": "skill_bundle",
                "source": self.source,
                "path": linked,
                "names": ["chatmaker"],
            }
        ]

        with self.assertRaises(UnsafeInstallPath):
            self._transaction().apply(changes)

        self.assertEqual(list(outside.iterdir()), [])

    def test_global_install_lock_serializes_concurrent_apply(self):
        entered = threading.Event()
        release = threading.Event()
        outcomes = []
        failures = []

        def inject(point, _context):
            if point == "skill_activation" and not entered.is_set():
                entered.set()
                if not release.wait(5):
                    raise TimeoutError("test did not release first transaction")

        first = InstallTransaction(
            root=self.management_root,
            installation_id="test-install",
            failure_injector=inject,
        )
        second = self._transaction()

        def run(transaction):
            try:
                outcomes.append(transaction.apply(self._changes()).status)
            except Exception as exc:  # pragma: no cover - asserted below
                failures.append(exc)

        thread_one = threading.Thread(target=run, args=(first,))
        thread_two = threading.Thread(target=run, args=(second,))
        thread_one.start()
        self.assertTrue(entered.wait(5), "first transaction never reached activation")
        thread_two.start()
        time.sleep(0.1)
        self.assertTrue(thread_two.is_alive(), "second transaction bypassed the install lock")
        release.set()
        thread_one.join(5)
        thread_two.join(5)

        self.assertEqual(failures, [])
        self.assertCountEqual(outcomes, ["installed", "already_current"])

    def test_global_lock_serializes_different_host_installation_ids(self):
        entered = threading.Event()
        release = threading.Event()
        outcomes = []
        failures = []

        def inject(point, _context):
            if point == "skill_activation" and not entered.is_set():
                entered.set()
                if not release.wait(5):
                    raise TimeoutError("test did not release first host")

        first = InstallTransaction(
            root=self.management_root,
            installation_id="codex-host",
            failure_injector=inject,
        )
        second = InstallTransaction(
            root=self.management_root,
            installation_id="workbuddy-host",
        )
        second_skills = self.root / "second-host" / "skills"
        second_config = self.root / "second-host" / "mcp.json"
        second_changes = [
            {**self._changes()[0], "path": second_skills},
            {**self._changes()[1], "path": second_config},
        ]

        def run(transaction, changes):
            try:
                outcomes.append(transaction.apply(changes).status)
            except Exception as exc:  # pragma: no cover - asserted below
                failures.append(exc)

        one = threading.Thread(target=run, args=(first, self._changes()))
        two = threading.Thread(target=run, args=(second, second_changes))
        one.start()
        self.assertTrue(entered.wait(5))
        two.start()
        time.sleep(0.1)
        self.assertTrue(two.is_alive(), "second host bypassed the global lock")
        release.set()
        one.join(5)
        two.join(5)

        self.assertEqual(failures, [])
        self.assertCountEqual(outcomes, ["installed", "installed"])
        self.assertEqual(len(list((self.management_root / "state").glob("*.json"))), 2)


if __name__ == "__main__":
    unittest.main()
