from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))


class UniversalInstallerTests(unittest.TestCase):
    """End-to-end filesystem behavior for the single public installer."""

    def setUp(self) -> None:
        from chatmaker.installers import auto  # noqa: PLC0415
        from chatmaker.installers import capabilities  # noqa: PLC0415
        from chatmaker.installers.hosts import CodexHostAdapter  # noqa: PLC0415

        self.auto = auto
        self.capabilities = capabilities
        self.CodexHostAdapter = CodexHostAdapter
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.home = self.root / "teacher home"
        self.state_root = self.home / ".chatmaker"
        self.codex_home = self.home / "Codex"
        self.workbuddy_home = self.home / "WorkBuddy"

    def _environment(self, *, codex: bool = False, workbuddy: bool = False) -> dict[str, str]:
        environment = {"PATH": "", "SHELL": "/bin/sh"}
        if codex:
            (self.codex_home / "skills").mkdir(parents=True)
            environment["CODEX_HOME"] = str(self.codex_home)
        if workbuddy:
            self.workbuddy_home.mkdir(parents=True)
            (self.workbuddy_home / "skills").mkdir()
            (self.workbuddy_home / "mcp.json").write_text(
                json.dumps({"mcpServers": {"keep": {"command": "other"}}}),
                encoding="utf-8",
            )
            environment["WORKBUDDY_HOME"] = str(self.workbuddy_home)
            environment["WORKBUDDY_CONFIG"] = str(self.workbuddy_home / "mcp.json")
        return environment

    def _run(self, command: str, *arguments: str, environment: dict[str, str]) -> dict[str, object]:
        # Hardware enumeration is covered by capability tests.  Keep this
        # suite's host writes and transaction behavior real and fast.
        with (
            mock.patch.object(self.capabilities.nano_mindplus, "scan_ports", return_value=[]),
            mock.patch.object(self.capabilities.nano_mindplus, "discover_installations", return_value=[]),
        ):
            return self.auto.run(
                [command, *arguments],
                home=self.home,
                environ=environment,
                transaction_root=self.state_root,
            )

    def test_dry_run_reports_writes_without_creating_user_files(self):
        """Catches a dry run that writes transaction state or host content."""
        environment = self._environment(codex=True)
        before = sorted(path.relative_to(self.home) for path in self.home.rglob("*"))

        result = self._run("auto", "--dry-run", environment=environment)

        after = sorted(path.relative_to(self.home) for path in self.home.rglob("*"))
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "planned")
        self.assertEqual([host["host"] for host in result["hosts"]], ["codex"])
        self.assertTrue(result["changes"])
        self.assertEqual(before, after)
        self.assertFalse(self.state_root.exists())

    def test_auto_installs_all_detected_hosts_and_preserves_other_mcp_servers(self):
        """Catches a universal install that skips a detected host or overwrites MCP data."""
        result = self._run("auto", environment=self._environment(codex=True, workbuddy=True))

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "installed")
        self.assertEqual([host["host"] for host in result["hosts"]], ["codex", "workbuddy"])
        self.assertIsInstance(result["transaction_id"], str)
        for root in (self.codex_home, self.workbuddy_home):
            self.assertEqual(
                {path.name for path in (root / "skills").iterdir() if path.is_dir()},
                {"chatmaker"},
            )
            self.assertTrue((root / "skills" / "chatmaker" / "SKILL.md").is_file())
            for specialist in ("chatduino", "chatweb", "chatcad"):
                self.assertTrue(
                    (
                        root
                        / "skills"
                        / "chatmaker"
                        / "internal_skills"
                        / specialist
                        / "SKILL.md"
                    ).is_file()
                )
        saved = json.loads((self.workbuddy_home / "mcp.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["mcpServers"]["keep"], {"command": "other"})
        self.assertEqual(
            saved["mcpServers"]["chatmaker"]["args"],
            ["-m", "chatmaker.integrations.mcp"],
        )
        active = json.loads(next((self.state_root / "state").glob("*.json")).read_text(encoding="utf-8"))
        self.assertEqual(
            {item["name"] for item in active["managed"] if item["kind"] == "skill"},
            {"chatmaker"},
        )
        self.assertEqual(
            {item["server_key"] for item in active["managed"] if item["kind"] == "mcp"},
            {"chatmaker"},
        )
        self.assertTrue(
            all("migrated_server_key" not in item for item in active["managed"])
        )

    def test_auto_migrates_only_the_historical_chatmaker_mcp_key(self):
        environment = self._environment(workbuddy=True)
        config = self.workbuddy_home / "mcp.json"
        original = {
            "mcpServers": {
                "keep": {"command": "other"},
                "arduino-nano-mindplus": {
                    "command": "python",
                    "args": ["-m", "chatmaker.integrations.mcp"],
                    "env": {"OLD": "1"},
                },
            },
            "hostSetting": True,
        }
        config.write_text(json.dumps(original, indent=2) + "\n", encoding="utf-8")

        installed = self._run("auto", environment=environment)
        first_bytes = config.read_bytes()
        repeated = self._run("auto", environment=environment)
        saved = json.loads(first_bytes)

        self.assertTrue(installed["success"])
        self.assertEqual(repeated["status"], "already_current")
        self.assertEqual(config.read_bytes(), first_bytes)
        self.assertNotIn("arduino-nano-mindplus", saved["mcpServers"])
        self.assertEqual(saved["mcpServers"]["keep"], {"command": "other"})
        self.assertEqual(saved["mcpServers"]["chatmaker"]["args"], ["-m", "chatmaker.integrations.mcp"])

    def test_auto_preserves_a_real_legacy_plugin_and_allows_coexistence(self):
        environment = self._environment(workbuddy=True)
        config = self.workbuddy_home / "mcp.json"
        legacy = {
            "command": "legacy-nano-server",
            "args": ["--stdio"],
            "env": {"TEACHER": "keep-byte-for-byte"},
        }
        config.write_text(
            json.dumps({"mcpServers": {"arduino-nano-mindplus": legacy}}, indent=2) + "\n",
            encoding="utf-8",
        )

        self._run("auto", environment=environment)
        saved = json.loads(config.read_text(encoding="utf-8"))

        self.assertEqual(saved["mcpServers"]["arduino-nano-mindplus"], legacy)
        self.assertIn("chatmaker", saved["mcpServers"])
        self.assertEqual(len(saved["mcpServers"]), 2)

    def test_real_legacy_plugin_added_after_migration_survives_repeat_and_uninstall(self):
        environment = self._environment(workbuddy=True)
        config = self.workbuddy_home / "mcp.json"
        historical = {
            "command": "python",
            "args": ["-m", "chatmaker.integrations.mcp"],
        }
        config.write_text(
            json.dumps({"mcpServers": {"arduino-nano-mindplus": historical}}),
            encoding="utf-8",
        )
        first = self._run("auto", environment=environment)
        self.assertTrue(first["success"])
        real_plugin = {
            "command": "nano-classroom-plugin",
            "args": ["--stdio"],
            "env": {"OWNER": "teacher"},
        }
        saved = json.loads(config.read_text(encoding="utf-8"))
        saved["mcpServers"]["arduino-nano-mindplus"] = real_plugin
        config.write_text(json.dumps(saved, indent=2) + "\n", encoding="utf-8")

        repeated = self._run("auto", environment=environment)

        self.assertTrue(repeated["success"])
        self.assertEqual(repeated["status"], "already_current")
        self.assertEqual(
            json.loads(config.read_text(encoding="utf-8"))["mcpServers"][
                "arduino-nano-mindplus"
            ],
            real_plugin,
        )

        removed = self._run("uninstall", environment=environment)

        self.assertTrue(removed["success"])
        after = json.loads(config.read_text(encoding="utf-8"))["mcpServers"]
        self.assertNotIn("chatmaker", after)
        self.assertEqual(after["arduino-nano-mindplus"], real_plugin)

    def test_specialist_skill_replacements_added_after_migration_survive_repeat_and_uninstall(self):
        environment = self._environment(codex=True)
        skills = self.codex_home / "skills"
        for specialist in ("chatduino", "chatweb", "chatcad"):
            legacy = skills / specialist
            legacy.mkdir()
            (legacy / "legacy.txt").write_text(
                f"historical {specialist}", encoding="utf-8"
            )

        installed = self._run("auto", environment=environment)

        self.assertTrue(installed["success"])
        self.assertEqual(
            {path.name for path in skills.iterdir() if path.is_dir()},
            {"chatmaker"},
        )
        for specialist in ("chatduino", "chatweb", "chatcad"):
            replacement = skills / specialist
            replacement.mkdir()
            (replacement / "owner.txt").write_text(
                f"teacher {specialist}", encoding="utf-8"
            )

        repeated = self._run("auto", environment=environment)

        self.assertTrue(repeated["success"])
        self.assertEqual(repeated["status"], "already_current")
        for specialist in ("chatduino", "chatweb", "chatcad"):
            self.assertEqual(
                (skills / specialist / "owner.txt").read_text(encoding="utf-8"),
                f"teacher {specialist}",
            )

        removed = self._run("uninstall", environment=environment)

        self.assertTrue(removed["success"])
        self.assertFalse((skills / "chatmaker").exists())
        for specialist in ("chatduino", "chatweb", "chatcad"):
            self.assertEqual(
                (skills / specialist / "owner.txt").read_text(encoding="utf-8"),
                f"teacher {specialist}",
            )

    def test_uninstall_restores_pre_migration_specialist_skills_when_slots_remain_empty(self):
        environment = self._environment(codex=True)
        skills = self.codex_home / "skills"
        for specialist in ("chatduino", "chatweb", "chatcad"):
            legacy = skills / specialist
            legacy.mkdir()
            (legacy / "legacy.txt").write_text(
                f"historical {specialist}", encoding="utf-8"
            )

        installed = self._run("auto", environment=environment)
        self.assertTrue(installed["success"])
        removed = self._run("uninstall", environment=environment)

        self.assertTrue(removed["success"])
        for specialist in ("chatduino", "chatweb", "chatcad"):
            self.assertEqual(
                (skills / specialist / "legacy.txt").read_text(encoding="utf-8"),
                f"historical {specialist}",
            )

    def test_restore_and_uninstall_recover_the_pre_migration_mcp_before_image(self):
        environment = self._environment(workbuddy=True)
        config = self.workbuddy_home / "mcp.json"
        original = {
            "mcpServers": {
                "arduino-nano-mindplus": {
                    "command": "python",
                    "args": ["-m", "chatmaker.integrations.mcp"],
                },
                "keep": {"command": "other"},
            },
            "hostSetting": True,
        }
        config.write_text(json.dumps(original, indent=2) + "\n", encoding="utf-8")

        installed = self._run("auto", environment=environment)
        restored = self._run(
            "restore", installed["transaction_id"], environment=environment
        )

        self.assertTrue(restored["success"])
        self.assertEqual(json.loads(config.read_text(encoding="utf-8")), original)

        installed_again = self._run("auto", environment=environment)
        self.assertTrue(installed_again["success"])
        uninstalled = self._run("uninstall", environment=environment)

        self.assertTrue(uninstalled["success"])
        self.assertEqual(json.loads(config.read_text(encoding="utf-8")), original)

    def test_migration_supersedes_old_managed_key_but_uninstall_keeps_original_baseline(self):
        from chatmaker.installers.transaction import InstallTransaction  # noqa: PLC0415

        environment = self._environment(workbuddy=True)
        config = self.workbuddy_home / "mcp.json"
        original = {"mcpServers": {"keep": {"command": "other"}}, "hostSetting": True}
        config.write_text(json.dumps(original, indent=2) + "\n", encoding="utf-8")
        legacy = {
            "command": "python",
            "args": ["-m", "chatmaker.integrations.mcp"],
        }
        prior = InstallTransaction(
            root=self.state_root,
            installation_id=self.auto.INSTALLATION_ID,
        ).apply(
            [
                {
                    "kind": "mcp_server",
                    "path": config,
                    "server_key": "arduino-nano-mindplus",
                    "server": legacy,
                }
            ]
        )
        self.assertTrue(prior["success"])

        migrated = self._run("auto", environment=environment)
        self.assertTrue(migrated["success"])
        saved = json.loads(config.read_text(encoding="utf-8"))
        self.assertNotIn("arduino-nano-mindplus", saved["mcpServers"])
        self.assertIn("chatmaker", saved["mcpServers"])

        removed = self._run("uninstall", environment=environment)

        self.assertTrue(removed["success"])
        self.assertEqual(json.loads(config.read_text(encoding="utf-8")), original)

    def test_repeat_auto_is_idempotent_and_reports_unchanged(self):
        """Catches repeat installation creating another transaction or changing host files."""
        environment = self._environment(codex=True)
        first = self._run("auto", environment=environment)
        state_before = sorted(path.relative_to(self.state_root) for path in self.state_root.rglob("*"))

        repeated = self._run("auto", environment=environment)

        self.assertTrue(repeated["success"])
        self.assertEqual(repeated["status"], "already_current")
        self.assertEqual(repeated["transaction_id"], first["transaction_id"])
        self.assertFalse(repeated["changes"])
        self.assertTrue(repeated["unchanged"])
        self.assertEqual(state_before, sorted(path.relative_to(self.state_root) for path in self.state_root.rglob("*")))

    def test_partial_host_and_missing_hardware_remain_successful_limited_capabilities(self):
        """Catches absent serial ports or Mind+ being treated as an install failure."""
        result = self._run("auto", environment=self._environment(codex=True))

        self.assertTrue(result["success"])
        self.assertEqual([host["host"] for host in result["hosts"]], ["codex"])
        self.assertFalse(any(port["eligible_for_upload"] for port in result["environment"]["serial"]["ports"]))
        self.assertFalse(result["environment"]["mindplus"]["available"])
        self.assertIn("install Mind+", " ".join(result["next_actions"]))
        self.assertIn("Connect a supported wired board", " ".join(result["next_actions"]))

    def test_explicit_skill_directory_is_an_advanced_generic_host_target(self):
        """Catches an explicit other-host path being ignored or guessed as a built-in host."""
        target = self.root / "another host" / "skills"
        result = self._run(
            "auto",
            "--skill-root",
            str(target),
            environment={"PATH": "", "SHELL": "/bin/sh"},
        )

        self.assertTrue(result["success"])
        self.assertEqual([host["host"] for host in result["hosts"]], ["explicit"])
        self.assertTrue((target / "chatmaker" / "SKILL.md").is_file())
        self.assertFalse((self.home / ".codex").exists())
        self.assertFalse((self.home / ".workbuddy").exists())

    def test_explicit_target_combines_with_detected_hosts_in_one_transaction(self):
        """Catches explicit paths replacing, rather than extending, detected hosts."""
        environment = self._environment(codex=True, workbuddy=True)
        target = self.root / "another host" / "skills"
        before = sorted(path.relative_to(self.home) for path in self.home.rglob("*"))

        planned = self._run(
            "auto", "--dry-run", "--skill-root", str(target), environment=environment
        )

        self.assertEqual([host["host"] for host in planned["hosts"]], ["codex", "workbuddy", "explicit"])
        self.assertEqual(before, sorted(path.relative_to(self.home) for path in self.home.rglob("*")))
        self.assertFalse(self.state_root.exists())
        self.assertFalse(target.exists())

        installed = self._run("auto", "--skill-root", str(target), environment=environment)
        repeated = self._run("auto", "--skill-root", str(target), environment=environment)

        self.assertTrue(installed["success"])
        self.assertEqual([host["host"] for host in installed["hosts"]], ["codex", "workbuddy", "explicit"])
        self.assertEqual(repeated["status"], "already_current")
        self.assertEqual(repeated["transaction_id"], installed["transaction_id"])
        self.assertEqual(
            [path.name for path in (self.state_root / "transactions").glob("*.json")],
            [f"{installed['transaction_id']}.json"],
        )
        for skill_root in (self.codex_home / "skills", self.workbuddy_home / "skills", target):
            self.assertTrue((skill_root / "chatmaker" / "SKILL.md").is_file())

    def test_doctor_verifies_workbuddy_split_skill_and_mcp_paths(self):
        """Catches doctor looking for Skills beside a separately configured MCP file."""
        environment = self._environment(workbuddy=True)
        config = self.root / "separate WorkBuddy config" / "mcp.json"
        config.parent.mkdir()
        config.write_text(json.dumps({"mcpServers": {"keep": {"command": "other"}}}), encoding="utf-8")
        environment["WORKBUDDY_CONFIG"] = str(config)

        self._run("auto", environment=environment)
        result = self._run("doctor", environment=environment)

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "healthy")
        self.assertEqual([host["host"] for host in result["hosts"]], ["workbuddy"])
        self.assertEqual(result["hosts"][0]["config"], str(config))
        self.assertTrue(result["hosts"][0]["mcp_server_ready"])

    def test_explicit_path_overlapping_a_detected_host_is_deduplicated(self):
        """Catches duplicate managed Skill identities in the combined transaction."""
        environment = self._environment(codex=True)
        target = self.codex_home / "skills"

        installed = self._run("auto", "--skill-root", str(target), environment=environment)

        self.assertTrue(installed["success"])
        self.assertEqual([host["host"] for host in installed["hosts"]], ["codex", "explicit"])
        self.assertEqual(len(installed["changes"]), 1)
        self.assertEqual(Path(installed["changes"][0].removeprefix("skill:")).name, "chatmaker")
        self.assertTrue((target / "chatmaker" / "SKILL.md").is_file())

    def test_doctor_reports_partial_multi_host_installation_without_writing(self):
        """Catches a partial Codex host masking healthy split-path WorkBuddy."""
        environment = self._environment(workbuddy=True)
        config = self.root / "separate WorkBuddy config" / "mcp.json"
        config.parent.mkdir()
        config.write_text(
            json.dumps({"mcpServers": {"keep": {"command": "other"}}}),
            encoding="utf-8",
        )
        environment["WORKBUDDY_CONFIG"] = str(config)
        self._run("auto", environment=environment)
        (self.codex_home / "skills").mkdir(parents=True)
        environment["CODEX_HOME"] = str(self.codex_home)
        before = {path: path.read_bytes() for path in self.home.rglob("*") if path.is_file()}

        result = self._run("doctor", environment=environment)

        after = {path: path.read_bytes() for path in self.home.rglob("*") if path.is_file()}
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "needs_install")
        self.assertEqual([host["host"] for host in result["hosts"]], ["codex", "workbuddy"])
        self.assertFalse(result["hosts"][0]["success"])
        self.assertTrue(result["hosts"][1]["success"])
        self.assertEqual(before, after)

    def test_doctor_verifies_an_explicit_skill_target_without_guessing_a_host(self):
        """Catches doctor reporting an installed explicit target as unsupported."""
        target = self.root / "another host" / "skills"
        environment = {"PATH": "", "SHELL": "/bin/sh"}
        self._run("auto", "--skill-root", str(target), environment=environment)

        result = self._run("doctor", "--skill-root", str(target), environment=environment)

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "healthy")
        self.assertEqual([host["host"] for host in result["hosts"]], ["explicit"])

    def test_doctor_is_read_only_and_reports_actual_installed_hosts(self):
        """Catches doctor mutating state or reporting a detected host as installed without files."""
        environment = self._environment(codex=True)
        self._run("auto", environment=environment)
        before = {path: path.read_bytes() for path in self.home.rglob("*") if path.is_file()}

        result = self._run("doctor", environment=environment)

        after = {path: path.read_bytes() for path in self.home.rglob("*") if path.is_file()}
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "healthy")
        self.assertTrue(result["hosts"][0]["success"])
        self.assertEqual(before, after)

    def test_doctor_delegates_verification_to_the_detected_host_adapter(self):
        """Catches doctor bypassing the adapter verification boundary."""
        environment = self._environment(codex=True)
        self._run("auto", environment=environment)

        with mock.patch.object(
            self.CodexHostAdapter,
            "verify",
            return_value={"success": True, "status": "healthy", "host": "codex"},
        ) as verify:
            result = self._run("doctor", environment=environment)

        verify.assert_called_once()
        self.assertTrue(result["success"])

    def test_restore_uses_the_transaction_id_and_returns_original_skill(self):
        """Catches restore ignoring its ID or failing to recover the transaction before-image."""
        environment = self._environment(codex=True)
        original = self.codex_home / "skills" / "chatmaker"
        original.mkdir()
        (original / "before.txt").write_text("teacher skill", encoding="utf-8")
        installed = self._run("auto", environment=environment)

        restored = self._run("restore", str(installed["transaction_id"]), environment=environment)

        self.assertTrue(restored["success"])
        self.assertEqual(restored["status"], "restored")
        self.assertEqual((original / "before.txt").read_text(encoding="utf-8"), "teacher skill")

    def test_uninstall_removes_managed_content_and_preserves_later_unrelated_mcp(self):
        """Catches uninstall deleting unrelated configuration added after installation."""
        environment = self._environment(codex=True, workbuddy=True)
        self._run("auto", environment=environment)
        config = self.workbuddy_home / "mcp.json"
        saved = json.loads(config.read_text(encoding="utf-8"))
        saved["mcpServers"]["later"] = {"command": "teacher-added"}
        config.write_text(json.dumps(saved), encoding="utf-8")

        result = self._run("uninstall", environment=environment)

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "uninstalled")
        self.assertFalse((self.codex_home / "skills" / "chatmaker").exists())
        saved = json.loads(config.read_text(encoding="utf-8"))
        self.assertNotIn("chatmaker", saved["mcpServers"])
        self.assertEqual(saved["mcpServers"]["keep"], {"command": "other"})
        self.assertEqual(saved["mcpServers"]["later"], {"command": "teacher-added"})

    def test_main_emits_a_single_json_object_for_the_public_cli(self):
        """Catches the script entry point emitting prose or omitting the required JSON keys."""
        environment = self._environment(codex=True)
        output = io.StringIO()
        with (
            mock.patch.object(self.capabilities.nano_mindplus, "scan_ports", return_value=[]),
            mock.patch.object(self.capabilities.nano_mindplus, "discover_installations", return_value=[]),
            contextlib.redirect_stdout(output),
        ):
            exit_code = self.auto.main(
                ["auto", "--dry-run", "--home", str(self.home), "--state-root", str(self.state_root)],
                environ=environment,
            )

        value = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(
            set(("success", "status", "environment", "hosts", "changes", "unchanged", "next_actions", "transaction_id")),
            set(value).intersection({"success", "status", "environment", "hosts", "changes", "unchanged", "next_actions", "transaction_id"}),
        )

    def test_main_returns_machine_readable_json_for_invalid_restore(self):
        """Catches CLI validation failures escaping as argparse prose."""
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = self.auto.main(["restore"], environ={"PATH": "", "SHELL": "/bin/sh"})

        value = json.loads(output.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertFalse(value["success"])
        self.assertEqual(value["status"], "failed")
        self.assertEqual(
            set(("success", "status", "environment", "hosts", "changes", "unchanged", "next_actions", "transaction_id")),
            set(value).intersection({"success", "status", "environment", "hosts", "changes", "unchanged", "next_actions", "transaction_id"}),
        )


if __name__ == "__main__":
    unittest.main()
