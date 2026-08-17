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

    def _single_skill_change(self):
        return {
            "kind": "skill_bundle",
            "source": self.source,
            "path": self.skills_root,
            "names": ["chatmaker"],
        }

    def _single_mcp_change(self):
        return {
            "kind": "mcp_server",
            "path": self.config,
            "server_key": "chatmaker-test",
            "server": {"type": "stdio", "command": "python", "args": ["-m", "test"]},
        }

    def _assert_active_transaction(self, transaction_id: str) -> None:
        state = json.loads(
            next((self.management_root / "state").glob("*.json")).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(state["phase"], "active")
        self.assertEqual(state["active_transaction_id"], transaction_id)

    def _assert_latest_operation_rolled_back(self) -> None:
        journals = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in (self.management_root / "transactions").glob("*.json")
        ]
        self.assertIn("rolled_back", {journal["status"] for journal in journals})

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

    def _migration_changes(self):
        return [
            {
                "kind": "skill_bundle",
                "source": self.source,
                "path": self.skills_root,
                "names": ["chatmaker"],
                "internal_names": ["chatduino", "chatweb"],
                "retire_names": ["chatduino", "chatweb"],
            },
            {
                "kind": "mcp_server",
                "path": self.config,
                "server_key": "chatmaker",
                "server": {
                    "type": "stdio",
                    "command": "python",
                    "args": ["-m", "chatmaker.integrations.mcp"],
                },
                "migrate_from_key": "arduino-nano-mindplus",
                "migrate_from_args": ["-m", "chatmaker.integrations.mcp"],
            },
        ]

    def _seed_migration_state(self) -> dict[str, object]:
        for name in ("chatduino", "chatweb"):
            skill = self.skills_root / name
            skill.mkdir(parents=True, exist_ok=True)
            (skill / "owner.txt").write_text(f"historical {name}", encoding="utf-8")
        original = {
            "theme": "dark",
            "mcpServers": {
                "arduino-nano-mindplus": {
                    "command": "python",
                    "args": ["-m", "chatmaker.integrations.mcp"],
                },
                "keep": {"command": "other"},
            },
        }
        self.config.parent.mkdir(parents=True, exist_ok=True)
        self.config.write_text(json.dumps(original), encoding="utf-8")
        return original

    def _assert_migration_original(self, original: dict[str, object]) -> None:
        self.assertFalse((self.skills_root / "chatmaker").exists())
        for name in ("chatduino", "chatweb"):
            self.assertEqual(
                (self.skills_root / name / "owner.txt").read_text(encoding="utf-8"),
                f"historical {name}",
            )
        self.assertEqual(json.loads(self.config.read_text(encoding="utf-8")), original)

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

    def test_skill_apply_race_returns_conflict_and_preserves_latest_external_write(self):
        self._seed_existing_state()
        edited = False

        def edit_before_replace(point, context):
            nonlocal edited
            if point == "skill_activation" and not edited:
                edited = True
                (Path(context["target"]) / "external.txt").write_text(
                    "latest skill write", encoding="utf-8"
                )

        result = InstallTransaction(
            root=self.management_root,
            installation_id="test-install",
            failure_injector=edit_before_replace,
        ).apply([self._single_skill_change()])

        self.assertFalse(result.success)
        self.assertEqual(result.status, "conflict")
        self.assertEqual(
            (self.skills_root / "chatmaker" / "external.txt").read_text(encoding="utf-8"),
            "latest skill write",
        )
        self.assertEqual(list((self.management_root / "state").glob("*.json")), [])
        self._assert_latest_operation_rolled_back()

    def test_mcp_apply_race_returns_conflict_and_preserves_latest_external_write(self):
        self._seed_existing_state()
        edited = False

        def edit_before_replace(point, context):
            nonlocal edited
            if point == "mcp_replacement" and not edited:
                edited = True
                data = json.loads(self.config.read_text(encoding="utf-8"))
                data["mcpServers"]["external-latest"] = {"command": "teacher"}
                self.config.write_text(json.dumps(data), encoding="utf-8")

        result = InstallTransaction(
            root=self.management_root,
            installation_id="test-install",
            failure_injector=edit_before_replace,
        ).apply([self._single_mcp_change()])

        self.assertFalse(result.success)
        self.assertEqual(result.status, "conflict")
        saved = json.loads(self.config.read_text(encoding="utf-8"))
        self.assertEqual(saved["mcpServers"]["external-latest"], {"command": "teacher"})
        self.assertEqual(saved["mcpServers"]["chatmaker-test"], {"command": "old"})
        self.assertEqual(list((self.management_root / "state").glob("*.json")), [])
        self._assert_latest_operation_rolled_back()

    def test_migration_verification_crash_recovers_every_before_image(self):
        original = self._seed_migration_state()
        crash, inject = self._crash_at("verification")
        transaction = InstallTransaction(
            root=self.management_root,
            installation_id="test-install",
            failure_injector=inject,
        )

        with self.assertRaises(crash):
            transaction.apply(self._migration_changes())

        self.assertEqual(self._transaction().uninstall().status, "already_absent")
        self._assert_migration_original(original)

    def test_migration_journal_replacement_crash_recovers_every_before_image(self):
        original = self._seed_migration_state()
        crash, inject = self._crash_at("journal_replacement")
        transaction = InstallTransaction(
            root=self.management_root,
            installation_id="test-install",
            failure_injector=inject,
        )

        with self.assertRaises(crash):
            transaction.apply(self._migration_changes())

        self.assertEqual(self._transaction().uninstall().status, "already_absent")
        self._assert_migration_original(original)

    def test_migration_state_replacement_crash_rolls_forward_without_repeating_migration(self):
        self._seed_migration_state()
        crash, inject = self._crash_at("state_replacement")
        transaction = InstallTransaction(
            root=self.management_root,
            installation_id="test-install",
            failure_injector=inject,
        )

        with self.assertRaises(crash):
            transaction.apply(self._migration_changes())

        recovered = self._transaction().apply(self._migration_changes())

        self.assertEqual(recovered.status, "already_current")
        self.assertEqual(
            {path.name for path in self.skills_root.iterdir() if path.is_dir()},
            {"chatmaker"},
        )
        saved = json.loads(self.config.read_text(encoding="utf-8"))["mcpServers"]
        self.assertNotIn("arduino-nano-mindplus", saved)
        self.assertIn("chatmaker", saved)

    def test_upgrade_from_legacy_four_entry_state_converges_to_one_managed_entry(self):
        chatcad_source = self.source / "chatcad"
        chatcad_source.mkdir(parents=True)
        (chatcad_source / "SKILL.md").write_text(
            "---\nname: chatcad\n---\nv1\n", encoding="utf-8"
        )
        legacy_names = ("chatmaker", "chatduino", "chatweb", "chatcad")
        for name in legacy_names:
            target = self.skills_root / name
            target.mkdir(parents=True, exist_ok=True)
            (target / "owner.txt").write_text(f"original {name}", encoding="utf-8")
        transaction = self._transaction()
        legacy = transaction.apply(
            [
                {
                    "kind": "skill_bundle",
                    "source": self.source,
                    "path": self.skills_root,
                    "names": list(legacy_names),
                }
            ]
        )
        self.assertTrue(legacy.success)

        migration = dict(self._migration_changes()[0])
        migration["internal_names"] = ["chatduino", "chatweb", "chatcad"]
        migration["retire_names"] = ["chatduino", "chatweb", "chatcad"]
        upgraded = transaction.apply([migration])

        self.assertTrue(upgraded.success)
        self.assertEqual(
            {path.name for path in self.skills_root.iterdir() if path.is_dir()},
            {"chatmaker"},
        )
        active = json.loads(
            next((self.management_root / "state").glob("*.json")).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            {item["name"] for item in active["managed"]},
            {"chatmaker"},
        )

        restored = transaction.restore(upgraded.transaction_id)

        self.assertEqual(restored.status, "restored")
        self.assertEqual(
            {path.name for path in self.skills_root.iterdir() if path.is_dir()},
            set(legacy_names),
        )
        self.assertTrue(
            all(
                "v1" in (self.skills_root / name / "SKILL.md").read_text(encoding="utf-8")
                for name in legacy_names
            )
        )

        upgraded_again = transaction.apply([migration])
        self.assertTrue(upgraded_again.success)
        removed = transaction.uninstall()

        self.assertEqual(removed.status, "uninstalled")
        for name in legacy_names:
            self.assertEqual(
                (self.skills_root / name / "owner.txt").read_text(encoding="utf-8"),
                f"original {name}",
            )

    def test_retired_skill_change_after_backup_aborts_without_installing_chatmaker(self):
        original = self._seed_migration_state()
        real_backup = transaction_module._atomic_backup
        raced = False

        def mutate_chatduino_after_backup(source, destination, source_guards=None):
            nonlocal raced
            real_backup(source, destination, source_guards=source_guards)
            if Path(source) == self.skills_root / "chatduino" and not raced:
                raced = True
                (Path(source) / "owner.txt").write_text(
                    "teacher concurrent edit", encoding="utf-8"
                )

        with mock.patch.object(
            transaction_module,
            "_atomic_backup",
            side_effect=mutate_chatduino_after_backup,
        ):
            result = self._transaction().apply([self._migration_changes()[0]])

        self.assertFalse(result.success)
        self.assertEqual(result.status, "conflict")
        self.assertFalse((self.skills_root / "chatmaker").exists())
        self.assertEqual(
            (self.skills_root / "chatduino" / "owner.txt").read_text(encoding="utf-8"),
            "teacher concurrent edit",
        )
        self.assertEqual(
            (self.skills_root / "chatweb" / "owner.txt").read_text(encoding="utf-8"),
            "historical chatweb",
        )
        self.assertEqual(json.loads(self.config.read_text(encoding="utf-8")), original)
        self.assertEqual(list((self.management_root / "state").glob("*.json")), [])
        self.assertEqual(list((self.management_root / "backups").glob("*")), [])

    def test_partial_retired_skill_backup_aborts_before_any_host_target_changes(self):
        original = self._seed_migration_state()
        real_backup = transaction_module._atomic_backup
        corrupted = False

        def corrupt_chatweb_backup(source, destination, source_guards=None):
            nonlocal corrupted
            real_backup(source, destination, source_guards=source_guards)
            if Path(source) == self.skills_root / "chatweb" and not corrupted:
                corrupted = True
                (Path(destination) / "owner.txt").write_text(
                    "partial copy", encoding="utf-8"
                )

        with mock.patch.object(
            transaction_module,
            "_atomic_backup",
            side_effect=corrupt_chatweb_backup,
        ):
            with self.assertRaises(InstallConflict):
                self._transaction().apply([self._migration_changes()[0]])

        self.assertFalse((self.skills_root / "chatmaker").exists())
        for name in ("chatduino", "chatweb"):
            self.assertEqual(
                (self.skills_root / name / "owner.txt").read_text(encoding="utf-8"),
                f"historical {name}",
            )
        self.assertEqual(json.loads(self.config.read_text(encoding="utf-8")), original)
        self.assertEqual(list((self.management_root / "state").glob("*.json")), [])
        self.assertEqual(list((self.management_root / "backups").glob("*")), [])

    def test_retired_skill_change_at_activation_is_preserved_while_other_writes_roll_back(self):
        original = self._seed_migration_state()
        raced = False

        def edit_when_migration_starts(point, context):
            nonlocal raced
            if (
                point == "skill_migration"
                and str(context["identity"]).endswith("chatduino")
                and not raced
            ):
                raced = True
                (self.skills_root / "chatduino" / "owner.txt").write_text(
                    "teacher last-moment edit", encoding="utf-8"
                )

        transaction = InstallTransaction(
            root=self.management_root,
            installation_id="test-install",
            failure_injector=edit_when_migration_starts,
        )
        result = transaction.apply([self._migration_changes()[0]])

        self.assertFalse(result.success)
        self.assertEqual(result.status, "conflict")
        self.assertFalse((self.skills_root / "chatmaker").exists())
        self.assertEqual(
            (self.skills_root / "chatduino" / "owner.txt").read_text(encoding="utf-8"),
            "teacher last-moment edit",
        )
        self.assertEqual(
            (self.skills_root / "chatweb" / "owner.txt").read_text(encoding="utf-8"),
            "historical chatweb",
        )
        self.assertEqual(json.loads(self.config.read_text(encoding="utf-8")), original)

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

    def test_skill_restore_race_preserves_latest_write_and_rolls_back_started_mcp_restore(self):
        self._seed_existing_state()
        installed = self._transaction().apply(self._changes())
        edited = False

        def edit_before_skill(point, context):
            nonlocal edited
            if (
                point == "restore_before_target"
                and str(context["identity"]).endswith("chatmaker")
                and not edited
            ):
                edited = True
                (self.skills_root / "chatmaker" / "external.txt").write_text(
                    "latest restore skill write", encoding="utf-8"
                )

        result = InstallTransaction(
            root=self.management_root,
            installation_id="test-install",
            failure_injector=edit_before_skill,
        ).restore(installed.transaction_id)

        self.assertFalse(result.success)
        self.assertEqual(result.status, "conflict")
        self.assertEqual(
            (self.skills_root / "chatmaker" / "external.txt").read_text(encoding="utf-8"),
            "latest restore skill write",
        )
        self.assertEqual(
            json.loads(self.config.read_text(encoding="utf-8"))["mcpServers"][
                "chatmaker-test"
            ]["args"],
            ["-m", "test"],
        )
        self._assert_active_transaction(installed.transaction_id)
        self._assert_latest_operation_rolled_back()

    def test_mcp_restore_race_returns_conflict_and_preserves_latest_external_write(self):
        self._seed_existing_state()
        installed = self._transaction().apply([self._single_mcp_change()])
        edited = False

        def edit_before_mcp(point, _context):
            nonlocal edited
            if point == "restore_before_target" and not edited:
                edited = True
                data = json.loads(self.config.read_text(encoding="utf-8"))
                data["mcpServers"]["external-latest"] = {"command": "teacher"}
                self.config.write_text(json.dumps(data), encoding="utf-8")

        result = InstallTransaction(
            root=self.management_root,
            installation_id="test-install",
            failure_injector=edit_before_mcp,
        ).restore(installed.transaction_id)

        self.assertFalse(result.success)
        self.assertEqual(result.status, "conflict")
        saved = json.loads(self.config.read_text(encoding="utf-8"))
        self.assertEqual(saved["mcpServers"]["external-latest"], {"command": "teacher"})
        self.assertEqual(saved["mcpServers"]["chatmaker-test"]["args"], ["-m", "test"])
        self._assert_active_transaction(installed.transaction_id)
        self._assert_latest_operation_rolled_back()

    def test_migration_restore_crash_preserves_new_plugin_and_skill_replacement(self):
        self._seed_migration_state()
        installed = self._transaction().apply(self._migration_changes())
        plugin = {"command": "teacher-nano", "args": ["--stdio"]}
        saved = json.loads(self.config.read_text(encoding="utf-8"))
        saved["mcpServers"]["arduino-nano-mindplus"] = plugin
        self.config.write_text(json.dumps(saved), encoding="utf-8")
        replacement = self.skills_root / "chatduino"
        replacement.mkdir()
        (replacement / "owner.txt").write_text("teacher replacement", encoding="utf-8")
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
        self.assertEqual(
            json.loads(self.config.read_text(encoding="utf-8"))["mcpServers"][
                "arduino-nano-mindplus"
            ],
            plugin,
        )
        self.assertEqual(
            (replacement / "owner.txt").read_text(encoding="utf-8"),
            "teacher replacement",
        )
        self.assertEqual(
            (self.skills_root / "chatweb" / "owner.txt").read_text(encoding="utf-8"),
            "historical chatweb",
        )

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

    def test_skill_uninstall_race_preserves_latest_write_and_rolls_back_started_mcp_uninstall(self):
        self._seed_existing_state()
        installed = self._transaction().apply(self._changes())
        edited = False

        def edit_before_skill(point, context):
            nonlocal edited
            if (
                point == "uninstall_before_target"
                and str(context["identity"]).endswith("chatmaker")
                and not edited
            ):
                edited = True
                (self.skills_root / "chatmaker" / "external.txt").write_text(
                    "latest uninstall skill write", encoding="utf-8"
                )

        result = InstallTransaction(
            root=self.management_root,
            installation_id="test-install",
            failure_injector=edit_before_skill,
        ).uninstall()

        self.assertFalse(result.success)
        self.assertEqual(result.status, "conflict")
        self.assertEqual(
            (self.skills_root / "chatmaker" / "external.txt").read_text(encoding="utf-8"),
            "latest uninstall skill write",
        )
        self.assertEqual(
            json.loads(self.config.read_text(encoding="utf-8"))["mcpServers"][
                "chatmaker-test"
            ]["args"],
            ["-m", "test"],
        )
        self._assert_active_transaction(installed.transaction_id)
        self._assert_latest_operation_rolled_back()

    def test_mcp_uninstall_race_returns_conflict_and_preserves_latest_external_write(self):
        self._seed_existing_state()
        installed = self._transaction().apply([self._single_mcp_change()])
        edited = False

        def edit_before_mcp(point, _context):
            nonlocal edited
            if point == "uninstall_before_target" and not edited:
                edited = True
                data = json.loads(self.config.read_text(encoding="utf-8"))
                data["mcpServers"]["external-latest"] = {"command": "teacher"}
                self.config.write_text(json.dumps(data), encoding="utf-8")

        result = InstallTransaction(
            root=self.management_root,
            installation_id="test-install",
            failure_injector=edit_before_mcp,
        ).uninstall()

        self.assertFalse(result.success)
        self.assertEqual(result.status, "conflict")
        saved = json.loads(self.config.read_text(encoding="utf-8"))
        self.assertEqual(saved["mcpServers"]["external-latest"], {"command": "teacher"})
        self.assertEqual(saved["mcpServers"]["chatmaker-test"]["args"], ["-m", "test"])
        self._assert_active_transaction(installed.transaction_id)
        self._assert_latest_operation_rolled_back()

    def test_migration_uninstall_crash_preserves_new_plugin_and_skill_replacement(self):
        self._seed_migration_state()
        self._transaction().apply(self._migration_changes())
        plugin = {"command": "teacher-nano", "args": ["--stdio"]}
        saved = json.loads(self.config.read_text(encoding="utf-8"))
        saved["mcpServers"]["arduino-nano-mindplus"] = plugin
        self.config.write_text(json.dumps(saved), encoding="utf-8")
        replacement = self.skills_root / "chatduino"
        replacement.mkdir()
        (replacement / "owner.txt").write_text("teacher replacement", encoding="utf-8")
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
        self.assertEqual(
            json.loads(self.config.read_text(encoding="utf-8"))["mcpServers"][
                "arduino-nano-mindplus"
            ],
            plugin,
        )
        self.assertEqual(
            (replacement / "owner.txt").read_text(encoding="utf-8"),
            "teacher replacement",
        )
        self.assertEqual(
            (self.skills_root / "chatweb" / "owner.txt").read_text(encoding="utf-8"),
            "historical chatweb",
        )

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

    def test_active_state_rejects_an_extra_managed_record_before_uninstall_mutation(self):
        installed = self._transaction().apply(self._changes())
        outside = transaction_module.canonical_install_path(
            self.root / "outside-extra-skill"
        )
        outside.mkdir()
        marker = outside / "SKILL.md"
        marker.write_text("user owned", encoding="utf-8")
        state_path = next((self.management_root / "state").glob("*.json"))
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["managed"].append(
            {
                "kind": "skill",
                "identity": f"skill:{outside}",
                "target": str(outside),
                "name": outside.name,
                "installed_hash": _path_hash(outside),
                "baseline": {
                    "before_exists": False,
                    "backup": None,
                    "before_hash": transaction_module._MISSING_HASH,
                    "transaction_id": installed.transaction_id,
                },
            }
        )
        state["managed"] = sorted(state["managed"], key=lambda item: item["identity"])
        state["managed_hash"] = transaction_module._aggregate_hash(state["managed"])
        state_path.write_text(json.dumps(state), encoding="utf-8")

        with self.assertRaises(InstallConflict):
            self._transaction().uninstall()

        self.assertEqual(marker.read_text(encoding="utf-8"), "user owned")
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

    @unittest.skipUnless(
        os.name == "posix" and hasattr(os, "O_NOFOLLOW"),
        "POSIX no-follow directory semantics only",
    )
    def test_posix_parent_swap_during_staging_never_writes_outside_target(self):
        self._seed_existing_state()
        outside = self.root / "outside-posix-staging"
        outside.mkdir()
        displaced = self.root / "displaced-posix-staging"
        swapped = False
        observed_outside_entries: list[str] = []

        def swap_then_observe(point, _context):
            nonlocal swapped
            if point != "staging":
                return
            if not swapped:
                os.rename(self.skills_root, displaced)
                os.symlink(outside, self.skills_root, target_is_directory=True)
                swapped = True
                return
            observed_outside_entries.extend(path.name for path in outside.iterdir())
            raise RuntimeError("stop after observing the staging destination")

        transaction = InstallTransaction(
            root=self.management_root,
            installation_id="test-install",
            failure_injector=swap_then_observe,
        )
        try:
            with self.assertRaises((UnsafeInstallPath, InstallConflict, RuntimeError, OSError)):
                transaction.apply(self._changes())
            self.assertTrue(swapped, "the POSIX parent swap did not run")
            self.assertEqual(observed_outside_entries, [])
        finally:
            if self.skills_root.is_symlink():
                self.skills_root.unlink()
            if displaced.exists() and not self.skills_root.exists():
                os.rename(displaced, self.skills_root)

    @unittest.skipUnless(
        os.name == "posix" and hasattr(os, "O_NOFOLLOW"),
        "POSIX no-follow directory semantics only",
    )
    def test_posix_parent_swap_during_cleanup_never_removes_outside_target(self):
        self._seed_existing_state()
        outside = self.root / "outside-posix-cleanup"
        outside.mkdir()
        displaced = self.root / "displaced-posix-cleanup"
        marker: Path | None = None
        swapped = False

        def swap_before_cleanup(point, context):
            nonlocal marker, swapped
            if point != "displaced_cleanup" or swapped:
                return
            outside_displaced = outside / Path(str(context["path"])).name
            outside_displaced.mkdir()
            marker = outside_displaced / "keep.txt"
            marker.write_text("outside user data", encoding="utf-8")
            os.rename(self.skills_root, displaced)
            os.symlink(outside, self.skills_root, target_is_directory=True)
            swapped = True

        transaction = InstallTransaction(
            root=self.management_root,
            installation_id="test-install",
            failure_injector=swap_before_cleanup,
        )
        try:
            with self.assertRaises(UnsafeInstallPath):
                transaction.apply(self._changes())
            self.assertTrue(swapped, "the POSIX cleanup swap did not run")
            self.assertIsNotNone(marker)
            assert marker is not None
            self.assertEqual(marker.read_text(encoding="utf-8"), "outside user data")
            self.assertEqual(list((self.management_root / "state").glob("*.json")), [])
        finally:
            if self.skills_root.is_symlink():
                self.skills_root.unlink()
            if displaced.exists() and not self.skills_root.exists():
                os.rename(displaced, self.skills_root)
        self._assert_original_state()

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
