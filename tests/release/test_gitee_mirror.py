import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml


class GiteeMirrorTests(unittest.TestCase):
    def test_tag_step_restores_annotation_after_checkout_peels_local_ref(self):
        git = shutil.which('git')
        bash = str(Path(git).parents[1] / 'bin/bash.exe') if os.name == 'nt' else shutil.which('bash')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            working = root / 'working'
            working.mkdir()

            def command(*args):
                result = subprocess.run([git, '-c', 'user.name=Test Fixture',
                    '-c', 'user.email=fixture@example.invalid', '-c', 'commit.gpgSign=false',
                    '-c', 'tag.gpgSign=false', *args], cwd=working, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                return result.stdout.strip()

            command('init', '--bare', str(root / 'origin.git'))
            command('init', '--bare', str(root / 'mirror.git'))
            command('init')
            command('commit', '--allow-empty', '-m', 'fixture')
            command('tag', '-a', 'release-test', '-m', 'annotated release')
            tag_object = command('rev-parse', 'refs/tags/release-test')
            command('remote', 'add', 'origin', str(root / 'origin.git'))
            command('remote', 'add', 'gitee', str(root / 'mirror.git'))
            command('push', 'origin', 'refs/tags/release-test')
            command('push', 'gitee', 'refs/tags/release-test')
            # actions/checkout can fetch the commit SHA into the local tag ref.
            command('update-ref', 'refs/tags/release-test', 'HEAD')
            self.assertNotEqual(command('rev-parse', 'refs/tags/release-test'), tag_object)

            workflow = yaml.safe_load((Path(__file__).resolve().parents[2] / '.github/workflows/mirror-gitee.yml').read_text('utf-8'))
            script = next(step['run'] for step in workflow['jobs']['mirror']['steps']
                          if step.get('name') == 'Push the GitHub tag')
            result = subprocess.run([bash, '-e', '-c', script], cwd=working,
                env={**os.environ, 'GITHUB_REF_NAME': 'release-test'}, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(command('rev-parse', 'refs/tags/release-test'), tag_object)
            self.assertEqual(command('ls-remote', 'gitee', 'refs/tags/release-test').split()[0], tag_object)
