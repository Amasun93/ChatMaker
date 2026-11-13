#!/bin/bash
set -euo pipefail

source_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
runtime_root=${CHATMAKER_RUNTIME_ROOT:-"$source_root/.chatmaker-runtime"}
python=${CHATMAKER_PYTHON:-python3}

if [[ ${1:-} != '' && ${1:-} != --check-only ]]; then
    printf '%s\n' 'Usage: bash scripts/setup_local_runtime.sh [--check-only]' >&2
    exit 2
fi

if ! command -v "$python" >/dev/null 2>&1; then
    printf '%s\n' '{"success":false,"error":"python_3_11_or_later_required"}'
    exit 1
fi

"$python" - "$source_root" "$runtime_root" "${1:-}" <<'PY'
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

source = Path(sys.argv[1]).resolve()
runtime = Path(sys.argv[2]).expanduser().resolve()
check_only = sys.argv[3] == '--check-only'
machine = platform.machine()
plan = {
    'action': 'setup-local-runtime', 'status': 'plan',
    'source_root': str(source), 'runtime_root': str(runtime),
    'python': sys.executable, 'architecture': machine,
}

if sys.version_info < (3, 11):
    print(json.dumps({**plan, 'success': False, 'error': 'python_3_11_or_later_required'}))
    sys.exit(1)
if platform.system() != 'Darwin' or machine not in {'arm64', 'x86_64'}:
    print(json.dumps({**plan, 'success': False, 'error': 'macos_required'}))
    sys.exit(1)
if check_only:
    print(json.dumps({**plan, 'success': True}))
    sys.exit(0)

registry = json.loads((source / 'runtime/chatmaker/installers/runtime_sources.json').read_text('utf-8'))
indexes = registry['pip_indexes']
if os.environ.get('CHATMAKER_DOWNLOAD_POLICY', '').strip().casefold() in {'domestic-only', 'domestic_only'}:
    indexes = [row for row in indexes if row['kind'] == 'domestic_mirror']

# Ignore host pip configuration and install into the project virtualenv.
environment = {key: value for key, value in os.environ.items() if not key.startswith(('PIP_', 'PYTHON'))}
environment['PIP_CONFIG_FILE'] = os.devnull
venv = runtime / 'venv'
venv_python = venv / 'bin/python3'

try:
    if not venv_python.is_file():
        if venv.exists():
            raise RuntimeError('existing_runtime_incomplete_choose_another_runtime_root')
        subprocess.run([sys.executable, '-m', 'venv', str(venv)], env=environment,
                       stdout=sys.stderr, check=True, timeout=120)
    probe = subprocess.run([str(venv_python), '-I', '-c',
                            'import platform,sys; print(platform.machine()); sys.exit(sys.version_info < (3,11))'],
                           capture_output=True, text=True, timeout=10)
    if probe.returncode or probe.stdout.strip() != machine:
        raise RuntimeError('existing_runtime_python_mismatch_choose_another_runtime_root')

    pip = [str(venv_python), '-m', 'pip', 'install', '--disable-pip-version-check', '--no-input']
    lock = source / 'distribution/core-runtime/requirements.lock'
    for index in indexes:
        try:
            result = subprocess.run([*pip, '--timeout', '20', '--retries', '1', '--index-url', index['url'],
                                     'setuptools==82.0.1', '-r', str(lock)],
                                    env=environment, stdout=sys.stderr, timeout=300)
        except subprocess.TimeoutExpired:
            continue
        if result.returncode == 0:
            break
    else:
        raise RuntimeError('pinned_python_dependencies_unavailable')
    subprocess.run([*pip, '--no-index', '--no-deps', '--no-build-isolation', '-e', str(source)],
                   env=environment, stdout=sys.stderr, check=True, timeout=120)

    bin_root = runtime / 'bin'
    bin_root.mkdir(exist_ok=True)
    for entry in (venv / 'bin').glob('chatmaker-*'):
        if not entry.is_file():
            continue
        wrapper = bin_root / entry.name
        temporary = wrapper.with_suffix('.tmp')
        temporary.write_text('#!/bin/sh\n'
                             'runtime=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P) || exit 1\n'
                             'export CHATMAKER_RUNTIME_ROOT="$runtime"\n'
                             'exec "$runtime/venv/bin/python3" -I "$runtime/venv/bin/${0##*/}" "$@"\n', encoding='utf-8')
        temporary.chmod(0o755)
        temporary.replace(wrapper)
    print(json.dumps({**plan, 'success': True, 'status': 'ready', 'python': str(venv_python),
                      'launcher_directory': str(bin_root), 'pip_source': index['id']}))
except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
    print(json.dumps({**plan, 'success': False, 'status': 'failed', 'error': str(exc)}))
    sys.exit(1)
PY
