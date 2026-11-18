"""Pinned, selective Arduino environments. No core install or global config writes."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path, PurePosixPath
import platform
import posixpath
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import uuid
import zipfile

from chatmaker.installers.downloads import (
    DownloadError, DownloadTooSlow, download_locked, download_session, load_runtime_sources, sha256,
    _candidate_sources, _write_json,
)
from chatmaker.installers.locks import exclusive_file, rename_directory
from chatmaker.progress import emit

ESP32_PROFILES = {'esp32', 'esp32s3', 'esp32c3', 'esp32c6'}
PROFILES = ESP32_PROFILES | {'avr', 'renesas_uno', 'unihiker_k10'}
WINDOWS_SHORT_HOMES = {'renesas_uno': 'r4', 'unihiker_k10': 'k10'}


def runtime_root() -> Path:
    return Path(os.environ.get('CHATMAKER_RUNTIME_ROOT', Path(__file__).resolve().parents[3] / '.chatmaker-runtime')).resolve()


def platform_tag() -> str | None:
    system, machine = platform.system(), platform.machine().lower()
    if system == 'Windows' and machine in {'amd64', 'x86_64'}:
        return 'windows-amd64'
    if system == 'Darwin' and machine in {'arm64', 'aarch64'}:
        return 'macos-arm64'
    if system == 'Darwin' and machine == 'x86_64':
        return 'macos-x86_64'
    return None


def rosetta_available() -> bool:
    try:
        probe = subprocess.run(['/usr/bin/arch', '-x86_64', '/usr/bin/true'],
                               capture_output=True, timeout=5)
        return probe.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def host_problem(*, dry_run=False) -> dict | None:
    tag = platform_tag()
    if tag is None:
        return {'success': False, 'error': 'unsupported_arduino_host',
                'teacher_message': '此 Arduino 工具链支持 Windows x64、Apple 芯片 Mac 和 Intel Mac。'}
    if not dry_run and tag == 'macos-arm64' and not rosetta_available():
        return {'success': False, 'error': 'rosetta_required',
                'teacher_message': 'Apple 芯片的 Mac 需要 Rosetta 运行 Arduino 的 Intel 版辅助工具。按 Apple 的安装说明准备后重试。'}
    return None


def _apply_esp32_release(data: dict, release: dict) -> None:
    # The approved release changes the core and its matching SDK archives.
    # The other dependencies and their host-specific archives stay identical.
    previous = data['core_version']
    version = release['core_version']
    data['core_version'] = version
    for name, metadata in release['artifacts'].items():
        item = data['artifacts'][name]
        item.update(metadata, version=version, filename=item['filename'].replace(previous, version),
                    destination=item['destination'].removesuffix(previous) + version)
        for source in item['sources']:
            source['url'] = source['url'].replace(previous, version)
        system = item['system']
        system.update(url=system['url'].replace(previous, version), archiveFileName=item['filename'],
                      checksum='SHA-256:' + item['sha256'], size=type(system['size'])(item['size']))
        if name == 'core':
            system['version'] = version
            for dependency in system['toolsDependencies']:
                if dependency['version'] == previous:
                    dependency['version'] = version
            data['platform'] = copy.deepcopy(system)


def bundle(profile: str = 'esp32', *, core_version: str | None = None) -> dict:
    if profile not in PROFILES:
        raise ValueError('unsupported_toolchain_profile')
    registry = load_runtime_sources()
    tag = platform_tag()
    if tag is None:
        raise ValueError('unsupported_arduino_host')
    esp = registry['arduino_esp32']
    result = copy.deepcopy(esp if profile in ESP32_PROFILES else registry['arduino_' + profile])
    if core_version is not None and core_version != result['core_version']:
        release = registry['arduino_esp32_preferred']
        if profile not in ESP32_PROFILES or core_version != release['core_version']:
            raise ValueError('unsupported_core_version')
        _apply_esp32_release(result, release)
    artifacts = result['artifacts']
    if profile not in ESP32_PROFILES:
        for name in result['common'] + result['optional_libraries']:
            if name not in artifacts:
                artifacts[name] = copy.deepcopy(esp['artifacts'][name])
    elif profile in {'esp32c3', 'esp32c6'}:
        result['common'] = ['esp-rv32' if name == 'esp-x32' else name for name in result['common']]
    artifacts['cli'] = registry['arduino_cli'][tag]
    result['fallback_cli'] = registry['arduino_cli_fallback'][tag]
    result['platform_tag'] = tag
    if tag.startswith('macos-'):
        macos = registry['arduino_macos']
        variants = {**macos['common'], **macos[tag]}
        host_artifacts = result.get('host_artifacts', {}).get(tag, {})
        artifacts.update(host_artifacts)
        for name, item in artifacts.items():
            if name in {'cli', 'core'} or name in host_artifacts or item['packager'] == 'library':
                continue
            if name.endswith('-libs') and item['packager'] == 'esp32':
                item['system']['host'] = tag.removeprefix('macos-') + '-apple-darwin'
                continue
            variant = variants[name]
            item.update({key: variant[key] for key in ('filename', 'size', 'sha256', 'sources')})
            item['system'] = {'host': variant['host'], 'url': item['sources'][-1]['url'],
                              'archiveFileName': item['filename'], 'size': str(item['size']),
                              'checksum': 'SHA-256:' + item['sha256']}
    return result


def home_for(profile: str, *, core_version: str | None = None) -> Path:
    if profile not in PROFILES:
        raise ValueError('unsupported_toolchain_profile')
    parent = runtime_root() / 'toolchains' / 'arduino'
    tag = platform_tag()
    if tag == 'windows-amd64' and profile in WINDOWS_SHORT_HOMES:
        # Older GCC packages use long multilib paths or repeated SDK include
        # flags that can exceed Windows' path and command-line limits.
        return runtime_root() / WINDOWS_SHORT_HOMES[profile]
    if tag and tag.startswith('macos-'):
        parent /= tag
    elif tag == 'windows-amd64' and profile in {'esp32c3', 'esp32c6'}:
        # This GCC build can exceed MAX_PATH with its relative include paths.
        parent = runtime_root() / 'rv'
    if core_version is None:
        return parent / profile
    name = profile.removeprefix('esp32') if parent.name == 'rv' else profile
    return parent / f'{name}-{core_version}'


def _environment_choices(profile: str, home: Path | None) -> list[tuple[Path, str | None]]:
    if home is not None or profile not in ESP32_PROFILES:
        return [((home or home_for(profile)).resolve(), None)]
    version = load_runtime_sources()['arduino_esp32_preferred']['core_version']
    return [(home_for(profile, core_version=version).resolve(), version), (home_for(profile).resolve(), None)]


def native(path: Path) -> Path:
    value = str(path.absolute())
    if os.name != 'nt' or value.startswith('\\\\?\\'):
        return path
    return Path('\\\\?\\UNC\\' + value[2:] if value.startswith('\\\\') else '\\\\?\\' + value)


def run_cli(command: list[str], timeout: int = 30, *, cpp_include: Path | str | None = None) -> dict:
    """CLI environment overrides take priority over --config-file; exclude them."""
    from .esp32_devkit_v1 import _run
    compiler_paths = {'CPATH', 'C_INCLUDE_PATH', 'CPLUS_INCLUDE_PATH', 'OBJC_INCLUDE_PATH',
                      'GCC_EXEC_PREFIX', 'COMPILER_PATH', 'LIBRARY_PATH'}
    environment = {key: value for key, value in os.environ.items()
                   if not key.upper().startswith('ARDUINO_') and key.upper() not in compiler_paths}
    if cpp_include is not None:
        environment['CPLUS_INCLUDE_PATH'] = str(cpp_include)
    if platform.system() == 'Darwin':
        # The ESP32 core calls python3 for its partition and upload recipes.
        environment['PATH'] = os.pathsep.join((str(Path(sys.executable).parent),
                                               environment.get('PATH') or os.defpath))
    return _run(command, timeout=timeout, env=environment)


def windows_cpp_include(context: dict) -> Path | str | None:
    if context.get('platform') != 'windows-amd64':
        return None
    # Give GCC the canonical directory. Its built-in search expands several
    # relative segments and can run out of Win32 path space on these targets.
    profile = context.get('profile')
    packages = Path(context['root']) / 'data/packages'
    if profile == 'esp32s3':
        tool = packages / 'esp32/tools/esp-x32/2601'
        cpp = tool / 'xtensa-esp-elf/include/c++/14.2.0'
        return os.pathsep.join((str(cpp), str(cpp / 'xtensa-esp-elf/esp32s3/no-rtti')))
    if profile == 'unihiker_k10':
        tool = packages / 'UNIHIKER/tools/xtensa-esp32s3-elf-gcc/esp-2021r2-patch5-8.4.0'
        cpp = tool / 'xtensa-esp32s3-elf/include/c++/8.4.0'
        return os.pathsep.join((str(cpp), str(cpp / 'xtensa-esp32s3-elf/no-rtti')))
    if profile == 'renesas_uno':
        tool = packages / 'arduino/tools/arm-none-eabi-gcc/7-2017q4'
        cpp = tool / 'arm-none-eabi/include/c++/7.2.1'
        return os.pathsep.join((str(cpp), str(cpp / 'arm-none-eabi/thumb/v7e-m/fpv4-sp/hard')))
    march = {'esp32c3': 'rv32imc_zicsr_zifencei', 'esp32c6': 'rv32imac_zicsr_zifencei'}.get(profile)
    if march is None:
        return None
    tool = packages / 'esp32/tools/esp-rv32/2601'
    return tool / 'riscv32-esp-elf/include/c++/14.2.0/riscv32-esp-elf' / march / 'ilp32/no-rtti'


def compile_properties(context: dict) -> list[str]:
    if context.get('platform') != 'windows-amd64' or context.get('profile') != 'unihiker_k10':
        return []
    # The vendor platform repeats the SDK path over 200 times. GCC supports a
    # shared prefix, retaining the regular -I search order without argv bloat.
    core = Path(context['root']) / 'data/packages/UNIHIKER/hardware/esp32' / context['core_version']
    property_name = 'compiler.cpreprocessor.flags.esp32s3'
    line = next(line for line in (core / 'platform.txt').read_text(encoding='utf-8-sig').splitlines()
                if line.startswith(property_name + '='))
    flags = line.split('=', 1)[1].replace('"-I{compiler.sdk.path}/', '-iwithprefixbefore "')
    flags = flags.replace('{runtime.platform.path}', core.as_posix())
    sdk_path = (core / 'tools/sdk/esp32s3').as_posix()
    return ['--build-property', f'{property_name}=-iprefix "{sdk_path}/" {flags}']


def safe_relative(name: str) -> Path:
    value = PurePosixPath(name)
    if not value.parts or value.is_absolute() or '..' in value.parts or '\\' in name or ':' in name:
        raise ValueError('unsafe_archive_path')
    return Path(*value.parts)


def file_manifest(directory: Path, *, exclude=()) -> dict:
    directory = native(directory)
    result = {}
    for path in sorted(directory.rglob('*')):
        if path.is_symlink():
            raise ValueError('component_symlink_not_allowed')
        relative = path.relative_to(directory).as_posix()
        if path.is_file() and relative not in exclude:
            digest = sha256(path)
            result[relative] = digest if os.name == 'nt' else {
                'sha256': digest, 'executable': bool(path.stat().st_mode & stat.S_IXUSR),
            }
    return result


def verify_manifest(directory: Path, manifest: dict, *, exclude=()) -> bool:
    try:
        return isinstance(manifest, dict) and bool(manifest) and file_manifest(directory, exclude=exclude) == manifest
    except (OSError, ValueError, TypeError):
        return False


def _write_archive_member(source, target: Path, mode: int) -> None:
    target = native(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with source, target.open('xb') as output:
        shutil.copyfileobj(source, output, 1024 * 1024)
    if os.name != 'nt':
        target.chmod(0o755 if mode & 0o111 else 0o644)


def _extract_tar(archive: Path, destination: Path, strip_root: bool) -> None:
    with tarfile.open(archive, 'r:*') as source:
        members = {}
        roots = set()
        for member in source.getmembers():
            if member.isdir() and PurePosixPath(member.name) == PurePosixPath('.'):
                continue
            relative = safe_relative(member.name)
            roots.add(relative.parts[0])
            if member.isdir():
                continue
            if not (member.isfile() or member.islnk() or member.issym()):
                raise ValueError('unsupported_tar_member')
            path = relative.as_posix()
            if path in members or (strip_root and len(relative.parts) == 1):
                raise ValueError('archive_root_mismatch')
            members[path] = member
        if not members or (strip_root and len(roots) != 1):
            raise ValueError('archive_root_mismatch')

        links = {}
        for path, member in members.items():
            if member.isfile():
                continue
            link = member.linkname
            if not link or PurePosixPath(link).is_absolute() or '\\' in link or ':' in link:
                raise ValueError('unsafe_archive_link')
            if member.issym():
                link = posixpath.join(posixpath.dirname(path), link)
            target = safe_relative(posixpath.normpath(link)).as_posix()
            if target not in members or not members[target].isfile():
                raise ValueError('unsafe_archive_link')
            links[path] = target

        def installed_path(path):
            parts = PurePosixPath(path).parts
            return destination.joinpath(*(parts[1:] if strip_root else parts))

        for path, member in members.items():
            if member.isfile():
                _write_archive_member(source.extractfile(member), installed_path(path), member.mode)
        # Official compiler archives contain file aliases. Store their bytes in
        # the component so its manifest covers every input without live links.
        for path, target in links.items():
            with native(installed_path(target)).open('rb') as content:
                _write_archive_member(content, installed_path(path), members[target].mode)


def extract_archive(archive: Path, destination: Path, *, strip_root: bool) -> None:
    if archive.name.endswith(('.tar.gz', '.tar.bz2', '.tar.xz')):
        _extract_tar(archive, destination, strip_root)
        return
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
            _write_archive_member(source.open(info), destination / relative, info.external_attr >> 16)


def selected(profile: str, libraries=(), *, core_version: str | None = None) -> tuple[dict, list[str]]:
    data = bundle(profile, core_version=core_version)
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
    platform_vendor = data['artifacts']['core']['packager']
    website = 'https://www.espressif.com' if platform_vendor == 'esp32' else 'https://www.arduino.cc'
    platform_metadata = data.get('package_metadata', {'websiteURL': website,
        'maintainer': 'Espressif Systems' if platform_vendor == 'esp32' else 'Arduino'})
    packages = []
    for vendor in (platform_vendor, 'builtin'):
        vendor_metadata = platform_metadata if vendor == platform_vendor else {'maintainer': 'Arduino', 'websiteURL': website}
        packages.append({'name': vendor, **vendor_metadata,
            'platforms': [platform_info] if vendor == platform_vendor else [],
            'tools': [{'name': t['name'], 'version': t['version'], 'systems': [t['system']]}
                      for t in tools if t['packager'] == vendor]})
    return {'packages': packages}


def generated_files(home: Path, data: dict, ids: list[str]) -> dict:
    index = offline_index(data, ids)
    core = data['artifacts']['core']['destination']
    installed = index
    version = data['artifacts']['cli'].get('installed_index_version')
    if version is not None:
        # Write the format the CLI expects so it does not migrate the file
        # during compilation and invalidate the verified environment.
        installed = {**index, 'IsTrusted': False, 'version': version}
    return {'arduino-cli.yaml': configuration(home), 'data/package_index.json': index,
            'data/library_index.json': {'libraries': []}, f'{core}/installed.json': installed}


def _artifact_ready(home: Path, name: str, item: dict) -> bool:
    try:
        receipt = json.loads((home / 'manifests' / (name + '.json')).read_text('utf-8'))
        return (receipt['sha256'] == item['sha256'] and receipt['destination'] == item['destination']
                and verify_manifest(home / item['destination'], receipt['files'],
                                    exclude=('installed.json',) if name == 'core' else ()))
    except (OSError, ValueError, KeyError, TypeError):
        return False


def _installed_cli(data: dict, home: Path) -> dict | None:
    for item in (data['artifacts']['cli'], data['fallback_cli']):
        if _artifact_ready(home, 'cli', item):
            return item
    return None


def search_roots_match(home: Path, data: dict, ids: list[str]) -> bool:
    """Reject extra selectable libraries, platforms or tool versions; never delete them."""
    expected = set(generated_files(home, data, ids))
    for name in ids:
        receipt = json.loads((home / 'manifests' / (name + '.json')).read_text('utf-8'))
        destination = data['artifacts'][name]['destination']
        expected.update((PurePosixPath(destination) / relative).as_posix() for relative in receipt['files'])
    for relative in ('data/packages', 'libraries', 'user/libraries', 'user/hardware'):
        directory = native(home / relative)
        if directory.is_symlink():
            return False
        actual = {(PurePosixPath(relative) / path.relative_to(directory).as_posix()).as_posix()
                  for path in directory.rglob('*') if path.is_file() or path.is_symlink()}
        required = {name for name in expected if name.startswith(relative + '/')}
        if actual != required:
            return False
    return True


def context(profile: str, *, libraries=(), home: Path | None = None) -> dict | None:
    for target, _ in _environment_choices(profile, home):
        ready = _verified_context(profile, libraries, target)
        if ready is not None:
            return ready
    return None


def _verified_context(profile: str, libraries, home: Path) -> dict | None:
    try:
        receipt = json.loads((home / 'receipt.json').read_text('utf-8'))
        installed = receipt['libraries']
        if receipt.get('schema') != 1 or receipt.get('profile') != profile or not set(libraries).issubset(installed):
            return None
        data, ids = selected(profile, installed, core_version=receipt.get('core_version'))
        if receipt['artifacts'] != ids:
            return None
        cli = _installed_cli(data, home)
        if cli is None:
            return None
        data['artifacts']['cli'] = cli
        if any(json.loads((home / name).read_text('utf-8')) != value
               for name, value in generated_files(home, data, ids).items()):
            return None
        if not all(_artifact_ready(home, name, data['artifacts'][name]) for name in ids if name != 'cli'):
            return None
        if not search_roots_match(home, data, ids):
            return None
        cli_name = 'arduino-cli.exe' if data['platform_tag'] == 'windows-amd64' else 'arduino-cli'
        return {'root': str(home), 'cli': str(home / 'bin' / cli_name),
                'config': str(home / 'arduino-cli.yaml'), 'libraries': str(home / 'libraries'),
                'profile': profile, 'platform': data['platform_tag'], 'core_version': data['core_version'],
                'cli_version': cli['version'], 'backend': 'chatmaker-managed-arduino',
                'installed_libraries': installed}
    except (OSError, ValueError, KeyError, TypeError):
        return None


def archive_path(item: dict) -> Path:
    return runtime_root() / 'downloads' / 'arduino' / item['filename']


def archive_matches(path: Path, item: dict) -> bool:
    return path.is_file() and path.stat().st_size == item['size'] and sha256(path) == item['sha256']


def _choose_cli(data: dict, home: Path) -> dict:
    installed = _installed_cli(data, home)
    if installed is not None:
        return installed
    preferred = data['artifacts']['cli']
    backup = data['fallback_cli']
    if not archive_matches(archive_path(preferred), preferred) and archive_matches(archive_path(backup), backup):
        return backup
    return preferred


def preview(profile: str, *, libraries=(), home: Path | None = None) -> dict:
    choices = _environment_choices(profile, home)
    ready = context(profile, libraries=libraries, home=home)
    if ready:
        home, core_version = Path(ready['root']), ready['core_version']
    else:
        home, core_version = choices[0]
    data, ids = selected(profile, libraries, core_version=core_version)
    preferred_cli = data['artifacts']['cli']
    data['artifacts']['cli'] = _choose_cli(data, home)
    components = []
    blocked = []
    for name in ids:
        item = data['artifacts'][name]
        cache = archive_path(item)
        cached = archive_matches(cache, item) or _artifact_ready(home, name, item)
        try:
            sources = _candidate_sources(item)
        except RuntimeError as exc:
            sources = []
            backup_sources = []
            if name == 'cli' and item is preferred_cli and not cached:
                try:
                    backup_sources = _candidate_sources(data['fallback_cli'])
                except DownloadError:
                    pass
            if not cached and not backup_sources:
                blocked.append({'component': name, 'error': str(exc)})
        components.append({'id': name, 'version': item['version'], 'archive_bytes': item['size'],
                           'filename': item['filename'], 'cached': cached, 'sources': sources})
    return {'success': True, 'action': 'prepare-environment', 'status': 'plan', 'profile': profile,
            'platform': data['platform_tag'], 'requires_rosetta': data['platform_tag'] == 'macos-arm64',
            'installation_performed': False, 'runtime_root': str(runtime_root()),
            'environment_root': str(home), 'components': components,
            'preferred_cli_version': preferred_cli['version'], 'fallback_cli_version': data['fallback_cli']['version'],
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
        if archive_matches(candidate, item):
            with exclusive_file(destination.with_name(destination.name + '.lock')):
                if destination.exists():
                    return
                temporary = destination.with_name(destination.name + '.seed')
                shutil.copyfile(candidate, temporary)
                temporary.replace(destination)
            return


def _download_cli(item: dict, backup: dict) -> tuple[dict, Path]:
    archive = archive_path(item)
    if item == backup:
        download_locked(item, archive)
        return item, archive
    try:
        download_locked(item, archive, retry_slow_sources=False)
    except DownloadError as preferred_error:
        emit('stage', stage='prepare', component='cli',
             message=f"新版 Arduino CLI 暂未取到，尝试兼容版 {backup['version']}")
        backup_archive = archive_path(backup)
        _seed_previous_cache(backup, backup_archive)
        try:
            download_locked(backup, backup_archive)
        except DownloadError as backup_error:
            if not isinstance(preferred_error, DownloadTooSlow):
                raise DownloadError(f'{preferred_error}; compatible_cli:{backup_error}') from backup_error
            # Both versions have been tried. Finish a working transfer if it
            # was deferred only to see whether the older copy would be faster.
            download_locked(item, archive)
        else:
            return backup, backup_archive
    return item, archive


def _choose_esp32_release(profile: str, libraries, choices: list[tuple[Path, str | None]]) -> tuple[Path, str | None]:
    preferred, compatible = choices
    artifacts = {}
    for home, version in choices:
        data, _ = selected(profile, libraries, core_version=version)
        artifacts[home] = [(name, data['artifacts'][name]) for name in ('core', *data['profiles'][profile])]

    def local(home, name, item):
        return archive_matches(archive_path(item), item) or _artifact_ready(home, name, item)

    # A fully cached compatible core can get the lesson running immediately.
    if not all(local(preferred[0], name, item) for name, item in artifacts[preferred[0]]) and all(
            local(compatible[0], name, item) for name, item in artifacts[compatible[0]]):
        return compatible

    def fetch(home, *, try_compatible):
        for name, item in artifacts[home]:
            if not _artifact_ready(home, name, item):
                archive = archive_path(item)
                _seed_previous_cache(item, archive)
                download_locked(item, archive, retry_slow_sources=not try_compatible)

    try:
        fetch(preferred[0], try_compatible=True)
    except DownloadError as preferred_error:
        emit('stage', stage='prepare', component='esp32', message='新版 ESP32 核心暂未取到，尝试上一兼容版')
        try:
            fetch(compatible[0], try_compatible=False)
        except DownloadError as backup_error:
            if not isinstance(preferred_error, DownloadTooSlow):
                raise DownloadError(f'{preferred_error}; compatible_esp32:{backup_error}') from backup_error
            fetch(preferred[0], try_compatible=False)
        else:
            return compatible
    return preferred


def _install(home: Path, name: str, item: dict, archive: Path) -> None:
    destination = (home / safe_relative(item['destination'])).resolve()
    if not destination.is_relative_to(home) or destination == home:
        raise ValueError('installation_path_outside_environment')
    stage_parent = home / '.staging'
    stage_parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=name + '-', dir=stage_parent))
    emit('stage', stage='extract', component=name, message='正在解压并核对组件')
    extract_archive(archive, stage, strip_root=item['strip_root'])
    # A vendor archive can ship its own installed.json. The managed index
    # replaces it after extraction and verifies the generated copy separately.
    manifest = file_manifest(stage, exclude=('installed.json',) if name == 'core' else ())
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        quarantine = (home / '.quarantine' / (name + '-' + uuid.uuid4().hex)).resolve()
        if not quarantine.is_relative_to(home):
            raise ValueError('quarantine_path_outside_environment')
        quarantine.parent.mkdir(parents=True, exist_ok=True)
        rename_directory(destination, quarantine)
    rename_directory(stage, destination)
    receipt_path = home / 'manifests' / (name + '.json')
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(receipt_path, {'sha256': item['sha256'], 'destination': item['destination'], 'files': manifest})


@download_session()
def prepare(profile: str, *, libraries=(), dry_run=False, home: Path | None = None) -> dict:
    problem = host_problem(dry_run=dry_run)
    if problem:
        return problem
    if dry_run:
        return preview(profile, libraries=libraries, home=home)
    emit('stage', stage='inspect', message='检查所需组件和已有缓存')
    ready = context(profile, libraries=libraries, home=home)
    if ready:
        return {'success': True, 'ready_for_compile': True, 'installation_performed': False, 'environment': ready}
    try:
        choices = _environment_choices(profile, home)
        home, core_version = (_choose_esp32_release(profile, libraries, choices) if len(choices) > 1 else choices[0])
        with exclusive_file(home / 'prepare.lock'):
            # If another prepare finished between source selection and lock acquisition, reuse it.
            ready = _verified_context(profile, libraries, home)
            if ready:
                return {'success': True, 'ready_for_compile': True, 'installation_performed': False, 'environment': ready}
            old_libraries = []
            try:
                old_libraries = json.loads((home / 'receipt.json').read_text('utf-8'))['libraries']
                selected(profile, old_libraries, core_version=core_version)
            except (OSError, ValueError, KeyError, TypeError):
                old_libraries = []
            data, ids = selected(profile, list(dict.fromkeys(list(old_libraries) + list(libraries))),
                                 core_version=core_version)
            data['artifacts']['cli'] = _choose_cli(data, home)
            for number, name in enumerate(ids, 1):
                item = data['artifacts'][name]
                emit('stage', stage='prepare', component=name, step=number, total_steps=len(ids),
                     message=f'准备组件 {number}/{len(ids)}')
                if _artifact_ready(home, name, item):
                    continue
                archive = archive_path(item)
                _seed_previous_cache(item, archive)
                if name == 'cli':
                    item, archive = _download_cli(item, data['fallback_cli'])
                    data['artifacts']['cli'] = item
                else:
                    download_locked(item, archive)
                _install(home, name, item, archive)
            for name, value in generated_files(home, data, ids).items():
                path = home / name
                path.parent.mkdir(parents=True, exist_ok=True)
                _write_json(path, value)
            for name in ('downloads', 'user', 'libraries', 'build-cache'):
                (home / name).mkdir(exist_ok=True)
            _write_json(home / 'receipt.json', {'schema': 1, 'profile': profile, 'artifacts': ids,
                        'core_version': data['core_version'],
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
