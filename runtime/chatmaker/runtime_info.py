"""Describe the code actually imported, rather than another checkout on PATH."""
from importlib.metadata import PackageNotFoundError, version
import os
from pathlib import Path
import subprocess
import sys
import tomllib


def identity() -> dict:
    source = Path(__file__).resolve().parents[2]
    commit = None
    dirty = None
    try:
        installed = version('chatmaker')
    except PackageNotFoundError:
        installed = None
    source_version = installed
    if (source / 'pyproject.toml').is_file():
        source_version = tomllib.loads((source / 'pyproject.toml').read_text('utf-8'))['project']['version']
    if (source / '.git').exists():
        try:
            result = subprocess.run(['git', '-C', str(source), 'rev-parse', 'HEAD'],
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                commit = result.stdout.strip()
                status = subprocess.run(['git', '-C', str(source), 'status', '--porcelain'],
                                        capture_output=True, text=True, timeout=5)
                dirty = bool(status.stdout.strip()) if status.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            pass
    return {'version': source_version, 'installed_version': installed,
            'source_root': str(source), 'source_commit': commit, 'source_dirty': dirty,
            'module_path': str(Path(__file__).resolve()), 'python': sys.executable,
            'runtime_root': str(Path(os.environ.get('CHATMAKER_RUNTIME_ROOT', source / '.chatmaker-runtime')).resolve())}
