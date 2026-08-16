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


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.installers import workbuddy  # noqa: E402
from chatmaker.installers.transaction import (  # noqa: E402
    InstallTransaction,
    UnsafeInstallPath,
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
        first = workbuddy.install(config, python_executable="python", source_skills=ROOT / "skills")
        backups_before = sorted((home / ".chatmaker" / "backups").glob("**/*"))

        second = workbuddy.install(config, python_executable="python", source_skills=ROOT / "skills")
        backups_after_second_install = sorted(
            (home / ".chatmaker" / "backups").glob("**/*")
        )
        saved = json.loads(config.read_text(encoding="utf-8"))
        saved["mcpServers"]["later"] = {"command": "keep-later"}
        config.write_text(json.dumps(saved), encoding="utf-8")
        removed = workbuddy.uninstall(config)
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


if __name__ == "__main__":
    unittest.main()
