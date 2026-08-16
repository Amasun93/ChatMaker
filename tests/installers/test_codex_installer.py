from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.installers.codex import doctor, install, uninstall  # noqa: E402
from chatmaker.installers import transaction  # noqa: E402


class CodexInstallerTests(unittest.TestCase):
    def test_uninstall_for_another_home_cannot_remove_the_installed_home(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home_a = root / "codex-a"
            home_b = root / "codex-b"
            transaction_root = root / ".chatmaker"
            installed = install(
                home_a,
                source_skills=ROOT / "skills",
                transaction_root=transaction_root,
            )

            wrong_home = uninstall(home_b, transaction_root=transaction_root)

            self.assertEqual(wrong_home["status"], "already_absent")
            self.assertTrue((home_a / "skills" / "chatmaker" / "SKILL.md").is_file())
            self.assertTrue(Path(installed["manifest"]).is_file())
            removed = uninstall(home_a, transaction_root=transaction_root)
            self.assertEqual(removed["status"], "uninstalled")

    def test_two_codex_homes_have_independent_transactions_and_uninstalls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home_a = root / "codex-a"
            home_b = root / "codex-b"
            transaction_root = root / ".chatmaker"

            installed_a = install(
                home_a,
                source_skills=ROOT / "skills",
                transaction_root=transaction_root,
            )
            installed_b = install(
                home_b,
                source_skills=ROOT / "skills",
                transaction_root=transaction_root,
            )

            self.assertEqual(installed_a["status"], "installed")
            self.assertEqual(installed_b["status"], "installed")
            self.assertNotEqual(installed_a["transaction_id"], installed_b["transaction_id"])
            self.assertEqual(len(list((transaction_root / "state").glob("*.json"))), 2)

            removed_a = uninstall(home_a, transaction_root=transaction_root)

            self.assertEqual(removed_a["status"], "uninstalled")
            self.assertFalse((home_a / "skills" / "chatmaker").exists())
            self.assertTrue((home_b / "skills" / "chatmaker" / "SKILL.md").is_file())
            removed_b = uninstall(home_b, transaction_root=transaction_root)
            self.assertEqual(removed_b["status"], "uninstalled")

    def test_install_and_uninstall_restore_existing_skill(self):
        with tempfile.TemporaryDirectory() as directory:
            codex_home = Path(directory) / ".codex"
            transaction_root = Path(directory) / ".chatmaker"
            old_chatduino = codex_home / "skills" / "chatduino"
            old_chatduino.mkdir(parents=True)
            (old_chatduino / "old-marker.txt").write_text("keep me", encoding="utf-8")

            installed = install(
                codex_home,
                source_skills=ROOT / "skills",
                transaction_root=transaction_root,
            )
            health = doctor(codex_home)

            self.assertTrue(installed["success"])
            self.assertEqual(installed["installed_skills"], ["chatmaker", "chatduino", "chatweb"])
            self.assertEqual(installed["content_manager"], "chatmaker-pack")
            self.assertEqual(installed["knowledge_packs_installed"], [])
            self.assertTrue(health["success"], health)
            self.assertEqual(health["content_manager"], "chatmaker-pack")
            self.assertEqual(health["knowledge_packs_installed"], [])
            self.assertFalse((old_chatduino / "old-marker.txt").exists())
            self.assertTrue((codex_home / "skills" / "chatmaker" / "SKILL.md").is_file())
            self.assertTrue(Path(installed["manifest"]).is_file())

            removed = uninstall(codex_home, transaction_root=transaction_root)

            self.assertTrue(removed["success"])
            self.assertEqual((old_chatduino / "old-marker.txt").read_text(encoding="utf-8"), "keep me")
            self.assertFalse((codex_home / "skills" / "chatmaker").exists())
            self.assertFalse((codex_home / "skills" / "chatweb").exists())
            self.assertTrue(Path(installed["manifest"]).exists(), "audit journal was removed")
            self.assertEqual(
                list((transaction_root / "state").glob("*.json")),
                [],
            )

    def test_second_install_preserves_the_original_restore_point(self):
        with tempfile.TemporaryDirectory() as directory:
            codex_home = Path(directory) / ".codex"
            transaction_root = Path(directory) / ".chatmaker"
            old_chatmaker = codex_home / "skills" / "chatmaker"
            old_chatmaker.mkdir(parents=True)
            (old_chatmaker / "old-marker.txt").write_text("original", encoding="utf-8")
            first = install(
                codex_home,
                source_skills=ROOT / "skills",
                transaction_root=transaction_root,
            )
            backups_before = sorted((transaction_root / "backups").glob("**/*"))

            second = install(
                codex_home,
                source_skills=ROOT / "skills",
                transaction_root=transaction_root,
            )

            self.assertEqual(first["status"], "installed")
            self.assertEqual(second["status"], "already_current")
            self.assertEqual(second["transaction_id"], first["transaction_id"])
            self.assertEqual(
                sorted((transaction_root / "backups").glob("**/*")),
                backups_before,
            )

            uninstall(codex_home, transaction_root=transaction_root)
            marker = old_chatmaker / "old-marker.txt"
            self.assertTrue(marker.is_file(), "original Skill was not restored")
            self.assertEqual(marker.read_text(encoding="utf-8"), "original")

    def test_mid_install_failure_rolls_back_activated_skills(self):
        with tempfile.TemporaryDirectory() as directory:
            codex_home = Path(directory) / ".codex"
            transaction_root = Path(directory) / ".chatmaker"
            old_chatmaker = codex_home / "skills" / "chatmaker"
            old_chatmaker.mkdir(parents=True)
            (old_chatmaker / "old-marker.txt").write_text("original", encoding="utf-8")
            real_activate = transaction._activate_staging

            def fail_when_activating_chatduino(source, target, *args):
                if Path(target).name == "chatduino":
                    raise PermissionError("simulated Windows directory activation failure")
                return real_activate(source, target, *args)

            with mock.patch.object(
                transaction,
                "_activate_staging",
                side_effect=fail_when_activating_chatduino,
            ):
                with self.assertRaises(PermissionError):
                    install(
                        codex_home,
                        source_skills=ROOT / "skills",
                        transaction_root=transaction_root,
                    )

            marker = old_chatmaker / "old-marker.txt"
            self.assertTrue(marker.is_file(), "original Skill was not restored after failure")
            self.assertEqual(marker.read_text(encoding="utf-8"), "original")
            self.assertFalse((codex_home / "skills" / "chatduino").exists())
            self.assertFalse((codex_home / "skills" / "chatweb").exists())
            self.assertFalse((codex_home / "chatmaker-codex-install.json").exists())

    def test_windows_directory_activation_permission_error_falls_back_to_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            codex_home = Path(directory) / ".codex"
            transaction_root = Path(directory) / ".chatmaker"
            real_replace = transaction.os.replace

            def reject_chatduino_rename(source, target):
                if Path(target).name == "chatduino":
                    raise PermissionError("simulated watcher lock")
                return real_replace(source, target)

            with mock.patch.object(transaction.os, "replace", side_effect=reject_chatduino_rename):
                try:
                    installed = install(
                        codex_home,
                        source_skills=ROOT / "skills",
                        transaction_root=transaction_root,
                    )
                except PermissionError as exc:
                    self.fail(f"directory activation did not fall back to copy: {exc}")

            self.assertTrue(installed["success"])
            self.assertTrue((codex_home / "skills" / "chatduino" / "SKILL.md").is_file())
            uninstall(codex_home, transaction_root=transaction_root)


if __name__ == "__main__":
    unittest.main()
