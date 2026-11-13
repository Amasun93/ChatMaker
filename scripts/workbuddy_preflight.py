#!/usr/bin/env python3
"""Check the checkout and installed runtime used for a WorkBuddy retest."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--runtime-root', type=Path)
    revision = parser.add_mutually_exclusive_group(required=True)
    revision.add_argument('--expected-revision')
    revision.add_argument('--expected-tag')
    args = parser.parse_args()

    source = args.source_root.expanduser().resolve()
    runtime = (args.runtime_root or Path(os.environ.get('CHATMAKER_RUNTIME_ROOT', source / '.chatmaker-runtime'))).expanduser().resolve()
    python = runtime / ('venv/Scripts/python.exe' if os.name == 'nt' else 'venv/bin/python3')
    report = {'action': 'workbuddy-preflight', 'hardware_test_performed': False}
    try:
        expected = args.expected_revision
        if args.expected_tag:
            tag = subprocess.run(['git', '-C', str(source), 'rev-parse', '--verify', '--end-of-options',
                                  f'refs/tags/{args.expected_tag}^{{commit}}'],
                                 capture_output=True, text=True, timeout=10)
            if tag.returncode:
                raise ValueError('release_tag_missing')
            expected = tag.stdout.strip()
        if not expected or re.fullmatch(r'[0-9a-f]{40}', expected) is None:
            raise ValueError('full_commit_sha_required')
        if not python.is_file():
            raise ValueError('runtime_missing')
        check = subprocess.run([str(python), '-I', '-m', 'chatmaker.hardware.workflow', '--version',
                                '--expect-source-root', str(source), '--expect-revision', expected],
                               env={**os.environ, 'CHATMAKER_RUNTIME_ROOT': str(runtime)},
                               capture_output=True, encoding='utf-8', timeout=20)
        if not check.stdout.strip():
            raise ValueError('runtime_entry_unavailable')
        value = json.loads(check.stdout)
        if check.returncode or not value.get('success'):
            raise ValueError(value.get('error', 'runtime_guard_failed'))
        identity = value['runtime']
        if identity['source_dirty'] is not False:
            raise ValueError('source_not_clean')
        if not identity['version'] or identity['version'] != identity['installed_version']:
            raise ValueError('installed_version_mismatch')
        # resolve() on the interpreter symlink would identify the global Python.
        if Path(identity['python']).absolute() != python or Path(identity['runtime_root']) != runtime:
            raise ValueError('runtime_path_mismatch')
        report.update(success=True, expected_revision=expected, runtime=identity)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        report.update(success=False, error=str(exc))
    print(json.dumps(report, ensure_ascii=True))
    return 0 if report['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
