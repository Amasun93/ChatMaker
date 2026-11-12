"""Pinned, selective Arduino environments. No core install or global config writes."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import stat
import tempfile
import uuid
import zipfile

from chatmaker.installers.downloads import download_locked, load_runtime_sources, sha256, _candidate_sources, _write_json
from chatmaker.installers.locks import exclusive_file
from chatmaker.progress import emit


def runtime_root() -> Path:
    return Path(os.environ.get('CHATMAKER_RUNTIME_ROOT', Path(__file__).resolve().parents[3] / '.chatmaker-runtime')).resolve()


def bundle() -> dict:
    registry = load_runtime_sources()
    result = copy.deepcopy(registry['arduino_esp32'])
    result['artifacts']['cli'] = registry['arduino_cli']['windows-amd64']
    return result


def home_for(profile: str) -> Path:
    if profile not in {'esp32', 'esp32s3'}:
        raise ValueError('unsupported_toolchain_profile')
    return runtime_root() / 'toolchains' / 'arduino' / profile


def native(path: Path) -> Path:
    value = str(path.absolute())
    if os.name != 'nt' or value.startswith('\\\\?\\'):
        return path
    return Path('\\\\?\\UNC\\' + value[2:] if value.startswith('\\\\') else '\\\\?\\' + value)


def safe_relative(name: str) -> Path:
    value = PurePosixPath(name)
    if not name or value.is_absolute() or '..' in value.parts or '\\' in name or ':' in name:
        raise ValueError('unsafe_archive_path')
    return Path(*value.parts)


def file_manifest(directory: Path, *, exclude=()) -> dict:
    directory = native(directory)
    return {p.relative_to(directory).as_posix(): sha256(p) for p in sorted(directory.rglob('*'))
            if p.is_file() and p.relative_to(directory).as_posix() not in exclude}


def verify_manifest(directory: Path, manifest: dict, *, exclude=()) -> bool:
    try:
        return isinstance(manifest, dict) and bool(manifest) and file_manifest(directory, exclude=exclude) == manifest
    except (OSError, ValueError, TypeError):
        return False


def extract_archive(archive: Path, destination: Path, *, strip_root: bool) -> None:
    with zipfile.ZipFile(archive) as source:
        members = []
        roots = set()
        for info in source.infolist():
            relative = safe_relative(info.filename)
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError('archive_links_not_supported')
            roots.add(relative.parts[0])
            if not info.is_dir():
                parts = relative.parts[1:] if strip_root else relative.parts
                if not parts:
                    raise ValueError('archive_root_mismatch')
                members.append((info, Path(*parts)))
        if not members or (strip_root and len(roots) != 1):
            raise ValueError('archive_root_mismatch')
        for info, relative in members:
            target = native(destination / relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            with source.open(info) as src, target.open('wb') as dst:
                shutil.copyfileobj(src, dst, 1024 * 1024)


def selected(profile: str, libraries=()) -> tuple[dict, list[str]]:
    data = bundle()
    if profile not in data['profiles']:
        raise ValueError('unsupported_toolchain_profile')
    if not isinstance(libraries, (list, tuple)) or any(name not in data['optional_libraries'] for name in libraries):
        raise ValueError('library_not_registered')
    return data, list(dict.fromkeys(['cli'] + data['common'] + data['profiles'][profile] + list(libraries)))


def configuration(home: Path) -> dict:
    return {'directories': {key: str(home / key) for key in ('data', 'downloads', 'user')},
            'build_cache': {'path': str(home / 'build-cache')},
            'board_manager': {'additional_urls': []}, 'metrics': {'enabled': False},
            'updater': {'enable_notification': False}}


def offline_index(data: dict, ids: list[str]) -> dict:
    platform_info = copy.deepcopy(data['platform'])
    tools = [data['artifacts'][name] for name in ids if name not in {'cli', 'core'}
             and data['artifacts'][name]['packager'] != 'library']
    platform_info['toolsDependencies'] = [d for d in platform_info['toolsDependencies']
        if any(t['packager'] == d['packager'] and t['name'] == d['name'] and t['version'] == d['version'] for t in tools)]
    packages = []
    for vendor in ('esp32', 'builtin'):
        packages.append({'name': vendor, 'maintainer': 'Espressif Systems' if vendor == 'esp32' else 'Arduino',
            'websiteURL': 'https://www.espressif.com' if vendor == 'esp32' else 'https://www.arduino.cc',
            'platforms': [platform_info] if vendor == 'esp32' else [],
            'tools': [{'name': t['name'], 'version': t['version'], 'systems': [t['system']]}
                      for t in tools if t['packager'] == vendor]})
    return {'packages': packages}


def generated_files(home: Path, data: dict, ids: list[str]) -> dict:
    index = offline_index(data, ids)
    core = data['artifacts']['core']['destination']
    return {'arduino-cli.yaml': configuration(home), 'data/package_index.json': index,
            'data/library_index.json': {'libraries': []}, f'{core}/installed.json': index}


def _artifact_ready(home: Path, name: str, item: dict) -> bool:
    try:
        receipt = json.loads((home / 'manifests' / (name + '.json')).read_text('utf-8'))
        return (receipt['sha256'] == item['sha256'] and receipt['destination'] == item['destination']
                and verify_manifest(home / item['destination'], receipt['files'],
                                    exclude=('installed.json',) if name == 'core' else ()))
    except (OSError, ValueError, KeyError, TypeError):
        return False


def context(profile: str, *, libraries=(), home: Path | None = None) -> dict | None:
    home = (home or home_for(profile)).resolve()
    try:
        receipt = json.loads((home / 'receipt.json').read_text('utf-8'))
        installed = receipt['libraries']
        if receipt.get('schema') != 1 or receipt.get('profile') != profile or not set(libraries).issubset(installed):
            return None
        data, ids = selected(profile, installed)
        if receipt['artifacts'] != ids:
            return None
        if any(json.loads((home / name).read_text('utf-8')) != value
               for name, value in generated_files(home, data, ids).items()):
            return None
        if not all(_artifact_ready(home, name, data['artifacts'][name]) for name in ids):
            return None
        return {'root': str(home), 'cli': str(home / 'bin/arduino-cli.exe'),
                'config': str(home / 'arduino-cli.yaml'), 'libraries': str(home / 'libraries'),
                'profile': profile, 'core_version': data['core_version'],
                'cli_version': data['artifacts']['cli']['version'], 'backend': 'chatmaker-managed-arduino',
                'installed_libraries': installed}
    except (OSError, ValueError, KeyError, TypeError):
        return None


def archive_path(item: dict) -> Path:
    return runtime_root() / 'downloads' / 'arduino' / item['filename']


def preview(profile: str, *, libraries=(), home: Path | None = None) -> dict:
    data, ids = selected(profile, libraries)
    components = []
    blocked = []
    for name in ids:
        item = data['artifacts'][name]
        cache = archive_path(item)
        cached = cache.is_file() and cache.stat().st_size == item['size'] and sha256(cache) == item['sha256']
        try:
            sources = _candidate_sources(item)
        except RuntimeError as exc:
            sources = []
            if not cached:
                blocked.append({'component': name, 'error': str(exc)})
        components.append({'id': name, 'version': item['version'], 'archive_bytes': item['size'],
                           'cached': cached, 'sources': sources})
    return {'success': True, 'action': 'prepare-environment', 'status': 'plan', 'profile': profile,
            'installation_performed': False, 'runtime_root': str(runtime_root()),
            'environment_root': str(home or home_for(profile)), 'components': components,
            'archive_bytes': sum(c['archive_bytes'] for c in components),
            'remaining_download_bytes': sum(c['archive_bytes'] for c in components if not c['cached']),
            'policy_blockers': blocked, 'estimated_seconds': None}


def _seed_previous_cache(item: dict, destination: Path) -> None:
    """Reuse only explicitly known project-local caches, after complete hashing."""
    previous = runtime_root() / 'toolchains/waveshare'
    candidates = [previous / 'downloads/packages' / item['filename']]
    if item['filename'].startswith('arduino-cli_'):
        candidates.append(previous / 'arduino-cli.zip')
    if destination.exists():
        return
    for candidate in candidates:
        if candidate.is_file() and candidate.stat().st_size == item['size'] and sha256(candidate) == item['sha256']:
            with exclusive_file(destination.with_name(destination.name + '.lock')):
                temporary = destination.with_name(destination.name + '.seed')
                shutil.copyfile(candidate, temporary)
                temporary.replace(destination)
            return


def _install(home: Path, name: str, item: dict, archive: Path) -> None:
    destination = (home / safe_relative(item['destination'])).resolve()
    if not destination.is_relative_to(home) or destination == home:
        raise ValueError('installation_path_outside_environment')
    stage_parent = home / '.staging'
    stage_parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=name + '-', dir=stage_parent))
    emit('stage', stage='extract', component=name, message='正在解压并核对组件')
    extract_archive(archive, stage, strip_root=item['strip_root'])
    manifest = file_manifest(stage)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        quarantine = (home / '.quarantine' / (name + '-' + uuid.uuid4().hex)).resolve()
        if not quarantine.is_relative_to(home):
            raise ValueError('quarantine_path_outside_environment')
        quarantine.parent.mkdir(parents=True, exist_ok=True)
        destination.rename(quarantine)
    stage.rename(destination)
    receipt_path = home / 'manifests' / (name + '.json')
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(receipt_path, {'sha256': item['sha256'], 'destination': item['destination'], 'files': manifest})


def prepare(profile: str, *, libraries=(), dry_run=False, home: Path | None = None) -> dict:
    home = (home or home_for(profile)).resolve()
    if dry_run:
        return preview(profile, libraries=libraries, home=home)
    if platform.system() != 'Windows' or platform.machine().lower() not in {'amd64', 'x86_64'}:
        return {'success': False, 'error': 'windows_x64_required'}
    emit('stage', stage='inspect', message='检查所需组件和已有缓存')
    ready = context(profile, libraries=libraries, home=home)
    if ready:
        return {'success': True, 'ready_for_compile': True, 'installation_performed': False, 'environment': ready}
    try:
        with exclusive_file(home / 'prepare.lock'):
            old_libraries = []
            try:
                old_libraries = json.loads((home / 'receipt.json').read_text('utf-8'))['libraries']
                selected(profile, old_libraries)
            except (OSError, ValueError, KeyError, TypeError):
                old_libraries = []
            data, ids = selected(profile, list(dict.fromkeys(list(old_libraries) + list(libraries))))
            for number, name in enumerate(ids, 1):
                item = data['artifacts'][name]
                emit('stage', stage='prepare', component=name, step=number, total_steps=len(ids),
                     message=f'准备组件 {number}/{len(ids)}')
                if _artifact_ready(home, name, item):
                    continue
                archive = archive_path(item)
                _seed_previous_cache(item, archive)
                download_locked(item, archive)
                _install(home, name, item, archive)
            for name, value in generated_files(home, data, ids).items():
                path = home / name
                path.parent.mkdir(parents=True, exist_ok=True)
                _write_json(path, value)
            for name in ('downloads', 'user', 'libraries', 'build-cache'):
                (home / name).mkdir(exist_ok=True)
            _write_json(home / 'receipt.json', {'schema': 1, 'profile': profile, 'artifacts': ids,
                        'libraries': [name for name in ids if name in data['optional_libraries']]})
            ready = context(profile, libraries=libraries, home=home)
            if not ready:
                raise ValueError('prepared_environment_not_verified')
            return {'success': True, 'ready_for_compile': True, 'installation_performed': True,
                    'environment': ready, 'archive_bytes': sum(data['artifacts'][name]['size'] for name in ids)}
    except Exception as exc:
        return {'success': False, 'ready_for_compile': False, 'error': 'environment_preparation_failed',
                'detail': str(exc), 'next_action': 'prepare-environment',
                'teacher_message': '准备尚未完成，已保留有效缓存和下载进度。查看具体组件与下载策略后重试，无需安装 Mind+。'}
