#!/bin/bash
set -euo pipefail

source_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
runtime_root=${CHATMAKER_RUNTIME_ROOT:-"$source_root/.chatmaker-runtime"}
if [[ $runtime_root == "~/"* ]]; then
    runtime_root="$HOME/${runtime_root:2}"
fi

if [[ ${1:-} != '' && ${1:-} != --check-only ]]; then
    printf '%s\n' 'Usage: bash scripts/setup_local_runtime.sh [--check-only]' >&2
    exit 2
fi

machine=$(uname -m)
if [[ $(uname -s) != Darwin || ( $machine != arm64 && $machine != x86_64 ) ]]; then
    printf '%s\n' '{"success":false,"error":"macos_required"}'
    exit 1
fi

registry="$source_root/runtime/chatmaker/installers/runtime_sources.json"
venv="$runtime_root/venv"
venv_python="$venv/bin/python3"
portable="$runtime_root/python/bin/python3"

python_usable() {
    local executable
    [[ -n $1 ]] || return 1
    executable=$(command -v "$1") || return 1
    # The system stub can show a developer tools installer on a clean Mac.
    if [[ $executable == /usr/bin/python3 ]] && ! xcode-select -p >/dev/null 2>&1; then
        return 1
    fi
    "$executable" -I -B -c '
import platform, ssl, sys, sysconfig
assert sys.version_info >= (3, 11) and platform.machine() == sys.argv[1]
assert platform.python_implementation() == "CPython" and not sysconfig.get_config_var("Py_GIL_DISABLED")
if sys.argv[2] == "venv":
    import pip._internal
    assert sys.prefix != sys.base_prefix
else:
    import ensurepip, venv
' "$machine" "$2" >/dev/null 2>&1
}

find_host_python() {
    local candidate
    for candidate in "${CHATMAKER_PYTHON:-}" python3 python python3.11; do
        if python_usable "$candidate" base; then
            command -v "$candidate"
            return
        fi
    done
    return 1
}

portable_field() {
    /usr/bin/plutil -extract "python.macos-$machine.$1" raw -o - "$registry"
}

verified_archive() {
    local checksum
    [[ -f $1 && $(/usr/bin/stat -f %z "$1") == "$2" ]] || return 1
    checksum=$(/usr/bin/shasum -a 256 "$1") || return 1
    [[ ${checksum%% *} == "$3" ]]
}

try_download() {
    local url=$1 part=$2 archive=$3 size=$4 sha256=$5
    printf '%s\n' 'Preparing project-local portable Python…' >&2
    /usr/bin/curl --location --fail --silent --show-error --connect-timeout 8 \
        --speed-limit 32768 --speed-time 12 --max-time 240 --output "$part" "$url" &&
        verified_archive "$part" "$size" "$sha256" &&
        mv -f -- "$part" "$archive"
}

install_portable() (
    local cache="$runtime_root/downloads"
    local filename size sha256 archive staging source kind url mirror
    filename=$(portable_field filename) || exit 1
    size=$(portable_field size) || exit 1
    sha256=$(portable_field sha256) || exit 1
    archive="$cache/$filename"
    mkdir -p -- "$cache" || exit 1
    staging=$(mktemp -d "$runtime_root/.portable-python.XXXXXX") || exit 1
    trap 'rm -f -- "$staging/download"; if [[ -d "$staging/python" ]]; then rm -rf -- "$staging/python"; fi; rmdir -- "$staging"' EXIT

    mirror=${CHATMAKER_DOWNLOAD_MIRROR_BASE:-}
    [[ -z $mirror || $mirror == https://* ]] || exit 1
    if ! verified_archive "$archive" "$size" "$sha256" &&
        ! { [[ -n $mirror ]] && try_download "${mirror%/}/$filename" "$staging/download" "$archive" "$size" "$sha256"; }; then
        source=0
        while kind=$(portable_field "sources.$source.kind" 2>/dev/null); do
            url=$(portable_field "sources.$source.url") || exit 1
            source=$((source + 1))
            case "${CHATMAKER_DOWNLOAD_POLICY:-}:$kind" in
                domestic-only:official_fallback|domestic_only:official_fallback) continue ;;
            esac
            try_download "$url" "$staging/download" "$archive" "$size" "$sha256" && break
        done
    fi
    verified_archive "$archive" "$size" "$sha256" || exit 1
    /usr/bin/tar -xzf "$archive" -C "$staging" || exit 1
    python_usable "$staging/python/bin/python3" base || exit 1
    quarantine "$runtime_root/python" || exit 1
    mv -- "$staging/python" "$runtime_root/python"
)

quarantine() {
    if [[ -e $1 || -L $1 ]]; then
        local backup
        backup=$(mktemp -d "$1.old.XXXXXX") || return 1
        mv -- "$1" "$backup/"
    fi
}

create_venv() {
    quarantine "$venv" || return 1
    "$1" -I -m venv "$venv" >&2 && python_usable "$venv_python" venv
}

if [[ ${1:-} != --check-only ]]; then
    mkdir -p -- "$runtime_root"
    if ! mkdir -- "$runtime_root/.setup.lock" 2>/dev/null; then
        printf '%s\n' '{"success":false,"error":"runtime_setup_in_progress"}'
        exit 1
    fi
    trap 'rmdir -- "$runtime_root/.setup.lock"' EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
fi

if python_usable "$venv_python" venv; then
    mode=existing-venv
    python="$venv_python"
elif python=$(find_host_python); then
    mode=existing-python
else
    mode=portable-python
    python="$portable"
fi

if [[ ${1:-} == --check-only && $mode == portable-python ]] && ! python_usable "$portable" base; then
    printf '{"success":true,"status":"plan","mode":"portable-python","architecture":"%s"}\n' "$machine"
    exit 0
fi
if [[ ${1:-} != --check-only && $mode != existing-venv ]]; then
    if [[ $mode == existing-python ]] && ! create_venv "$python"; then
        mode=portable-python
    fi
    if [[ $mode == portable-python ]]; then
        if ! python_usable "$portable" base && ! install_portable; then
            printf '%s\n' '{"success":false,"error":"portable_python_unavailable"}'
            exit 1
        fi
        if ! create_venv "$portable"; then
            printf '%s\n' '{"success":false,"error":"project_venv_creation_failed"}'
            exit 1
        fi
    fi
    python="$venv_python"
fi

"$python" -I - "$source_root" "$runtime_root" "${1:-}" "$mode" <<'PY'
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
    'python': sys.executable, 'architecture': machine, 'mode': sys.argv[4],
}

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
    pip = [str(venv_python), '-I', '-m', 'pip', 'install', '--disable-pip-version-check', '--no-input']
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
