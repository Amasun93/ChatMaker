import importlib.util
from contextlib import nullcontext
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'skills/chatmaker/scripts/chatmaker_version.py'
SPEC = importlib.util.spec_from_file_location('chatmaker_version', SCRIPT)
version = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(version)


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


class ChatMakerVersionTests(unittest.TestCase):
    def test_official_lookup_uses_pinned_mirror_after_primary_error(self):
        revision = 'a' * 40
        metadata = '[project]\nversion = "0.2.0b6"\n'
        tree = {'truncated': False, 'tree': [
            {'type': 'blob', 'path': f'skills/{name}/SKILL.md', 'sha': 'b' * 40}
            for name in ('chatmaker', *version.SPECIALISTS)
        ] + [{'type': 'blob', 'path': 'pyproject.toml', 'sha': version.blob_hash(metadata.encode())}]}
        with patch.object(version, 'read_url', side_effect=[
                OSError('primary unavailable'), json.dumps({'commit': {'sha': revision}}), json.dumps(tree), metadata,
        ]) as read:
            target, _ = version.official_target()
        self.assertEqual(target['source'], 'Gitee')
        self.assertEqual(target['commit'], revision)
        self.assertTrue(all(revision in call.args[0] for call in read.call_args_list[-2:]))

    def test_copied_skill_with_same_version_detects_changed_specialist(self):
        with tempfile.TemporaryDirectory() as directory:
            skill = Path(directory) / 'chatmaker'
            files = [(skill, 'chatmaker')]
            files.extend((skill / 'internal_skills' / name, name) for name in version.SPECIALISTS)
            blobs = {}
            for folder, name in files:
                folder.mkdir(parents=True)
                (folder / 'SKILL.md').write_bytes(b'current\r\n')
                blobs[f'skills/{name}/SKILL.md'] = version.blob_hash(b'current\n')
            target = {'source': 'GitHub', 'commit': 'b' * 40, 'version': '0.2.0b6'}
            args = SimpleNamespace(action='check-update', skill_dir=skill, checkout=None, runtime_root=None)
            with patch.object(version, 'official_target', return_value=(target, blobs)):
                current = version.run(args)
                self.assertFalse(current['update_available'])
                self.assertEqual(current['skill']['verified_against_commit'], target['commit'])
                (skill / 'internal_skills/chatweb/SKILL.md').write_bytes(b'old\n')
                stale = version.run(args)
                self.assertTrue(stale['update_available'])
                args.action = 'update'
                self.assertEqual(version.run(args)['status'], 'host_skill_update_required')

    def test_same_package_version_does_not_hide_old_runtime_commit(self):
        target = {'version': '0.2.0b6', 'commit': 'a' * 40}
        identity = {'version': target['version'], 'installed_version': target['version'],
                    'status': 'checked', 'source_dirty': False, 'source_commit': 'b' * 40}
        self.assertFalse(version.runtime_matches(identity, target))
        self.assertIsNone(version.runtime_matches({**identity, 'source_dirty': True}, target))

    def test_source_update_uses_git_and_preserves_local_edits_and_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            sandbox = Path(directory)
            server = sandbox / 'upstream'
            server.mkdir()
            git(server, 'init', '-b', 'main')
            git(server, 'config', 'user.name', 'ChatMaker Test')
            git(server, 'config', 'user.email', 'chatmaker@example.invalid')
            skill = server / 'skills/chatmaker/SKILL.md'
            skill.parent.mkdir(parents=True)
            skill.write_text('old', encoding='utf-8')
            (server / '.gitignore').write_text('.chatmaker-runtime/\n', encoding='utf-8')
            git(server, 'add', '--all')
            git(server, 'commit', '-m', 'old')
            checkout = sandbox / 'checkout'
            git(server, 'clone', str(server), str(checkout))
            git(checkout, 'remote', 'set-url', 'origin', version.REPOSITORIES['GitHub'][0] + '.git')
            before = git(checkout, 'rev-parse', 'HEAD')
            skill.write_text('new', encoding='utf-8')
            git(server, 'commit', '-am', 'new')
            target = {'source': 'GitHub', 'commit': git(server, 'rev-parse', 'HEAD'), 'version': '0.2.0b6'}
            cache = checkout / '.chatmaker-runtime/toolchains'
            cache.mkdir(parents=True)
            artifact = cache / 'already-installed'
            artifact.write_bytes(b'tools')

            def local_fetch(root, *args, **kwargs):
                if args[0] == 'fetch':
                    args = (*args[:-2], str(server), args[-1])
                return git_command(root, *args, **kwargs)

            git_command = version.git
            with patch.object(version, 'git', side_effect=local_fetch):
                local_skill = checkout / 'skills/chatmaker/SKILL.md'
                local_skill.write_text('local edit', encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'checkout_has_local_changes'):
                    version.update_checkout(checkout, target, None, {})
                self.assertEqual(local_skill.read_text(encoding='utf-8'), 'local edit')
                self.assertEqual(git(checkout, 'rev-parse', 'HEAD'), before)
                git(checkout, 'restore', '--', 'skills/chatmaker/SKILL.md')
                changed, _ = version.update_checkout(checkout, target, None, {})
                self.assertTrue(changed)
                self.assertFalse(version.update_checkout(checkout, target, None, {})[0])
            self.assertEqual(git(checkout, 'rev-parse', 'HEAD'), target['commit'])
            self.assertEqual(artifact.read_bytes(), b'tools')

    def test_offline_self_check_runs_as_a_standalone_script(self):
        result = subprocess.run([sys.executable, '-I', str(SCRIPT), 'self-check'], check=True,
                                capture_output=True, text=True)
        report = json.loads(result.stdout)
        self.assertTrue(report['success'])
        self.assertEqual(Path(report['skill']['path']), SCRIPT.parents[1])
        self.assertEqual(report['status'], 'local_check')

    def test_runtime_refresh_can_resume_if_python_was_left_incomplete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.git').mkdir()
            runtime = root / '.chatmaker-runtime'
            runtime.mkdir()
            pending = runtime / version.REFRESH_PENDING
            pending.write_text(str(root), encoding='utf-8')
            target = {'commit': 'a' * 40, 'version': '0.2.0b6'}
            before = version.inspect_runtime(runtime)
            self.assertEqual(before['status'], 'runtime_refresh_needed')
            self.assertEqual(before['source_root'], str(root))
            ready = {'status': 'checked', 'source_root': str(root), 'source_commit': target['commit'],
                     'source_dirty': False, 'version': target['version'], 'installed_version': target['version']}
            inspect = version.inspect_runtime

            def runtime_state(path):
                return inspect(path) if pending.exists() else ready

            with (patch.object(version, 'official_main', return_value=target['commit']),
                  patch.object(version, 'checkout_lock', return_value=nullcontext()),
                  patch.object(version, 'inspect_runtime', side_effect=runtime_state),
                  patch.object(version, 'command', return_value=SimpleNamespace(returncode=0)) as setup):
                changed, report = version.update_checkout(root, target, runtime, before)
            self.assertFalse(changed)
            setup.assert_called_once()
            self.assertTrue(version.runtime_matches(report, target))
            self.assertFalse(pending.exists())


if __name__ == '__main__':
    unittest.main()
