"""Move pinned Arduino archives between ChatMaker caches for offline setup."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

from chatmaker.installers.downloads import sha256
from chatmaker.installers.locks import exclusive_file

from . import arduino_toolchain as chain


def _selected_archives(profile: str, libraries, *, include_fallback=False) -> tuple[str, dict[str, dict]]:
    choices = chain._environment_choices(profile, None)
    archives = {}
    for _, version in choices:
        data, names = chain.selected(profile, libraries, core_version=version)
        backup = data['fallback_cli']
        cli = data['artifacts']['cli']
        items = [data['artifacts'][name] for name in names]
        if include_fallback:
            items.append(backup)
        else:
            if not chain.archive_matches(chain.archive_path(cli), cli) and chain.archive_matches(chain.archive_path(backup), backup):
                items[0] = backup
            archives = {item['filename']: item for item in items}
            if all(chain.archive_matches(chain.archive_path(item), item) for item in items):
                break
        archives.update((item['filename'], item) for item in items)
    return data['platform_tag'], archives


def _copy_verified(source, destination, item: dict, error: str) -> None:
    digest = hashlib.sha256()
    size = 0
    for block in iter(lambda: source.read(1024 * 1024), b''):
        size += len(block)
        if size > item['size']:
            raise ValueError(error)
        digest.update(block)
        destination.write(block)
    if size != item['size'] or digest.hexdigest() != item['sha256']:
        raise ValueError(error)


def export_cache(profile: str, libraries, output: Path) -> dict:
    platform_tag, archives = _selected_archives(profile, libraries)
    output = output.expanduser().resolve()
    paths = {name: chain.archive_path(item) for name, item in archives.items()}
    if output in {source.resolve() for source in paths.values()}:
        raise ValueError('cache_bundle_output_overlaps_input')

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.arduino-cache-', dir=output.parent) as folder:
        temporary = Path(folder) / 'archives.zip'
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_STORED) as bundle:
            for name, source in paths.items():
                item = archives[name]
                error = f'verified_cache_archive_missing:{name}'
                with exclusive_file(source.with_name(source.name + '.lock')):
                    if not source.is_file() or source.stat().st_size != item['size']:
                        raise ValueError(error)
                    entry = zipfile.ZipInfo(name)
                    entry.file_size = item['size']
                    with source.open('rb') as content, bundle.open(entry, 'w') as target:
                        _copy_verified(content, target, item, error)
        size = temporary.stat().st_size
        digest = sha256(temporary)
        temporary.replace(output)
    return {'success': True, 'action': 'export', 'bundle': str(output), 'size': size, 'sha256': digest,
            'profile': profile, 'platform': platform_tag, 'archives': list(paths)}


def import_cache(profile: str, libraries, source: Path) -> dict:
    platform_tag, archives = _selected_archives(profile, libraries, include_fallback=True)
    source = source.expanduser().resolve()
    imported = []
    reused = []
    with zipfile.ZipFile(source) as bundle:
        members = bundle.infolist()
        names = {member.filename for member in members}
        if not names or len(names) != len(members) or not names <= archives.keys():
            raise ValueError('cache_bundle_unexpected_member')
        for member in members:
            if member.is_dir() or member.file_size != archives[member.filename]['size']:
                raise ValueError(f'cache_bundle_member_mismatch:{member.filename}')
        root = chain.archive_path(archives[members[0].filename]).parent
        if source in {chain.archive_path(archives[name]).resolve() for name in names}:
            raise ValueError('cache_bundle_input_overlaps_destination')

        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.arduino-cache-', dir=root) as folder:
            stage = Path(folder)
            for member in members:
                name = member.filename
                temporary = stage / name
                with bundle.open(member) as content, temporary.open('xb') as output:
                    _copy_verified(content, output, archives[name], f'cache_bundle_member_mismatch:{name}')
            for member in members:
                name = member.filename
                item = archives[name]
                destination = chain.archive_path(item)
                with exclusive_file(destination.with_name(destination.name + '.lock')):
                    if chain.archive_matches(destination, item):
                        reused.append(name)
                    else:
                        (stage / name).replace(destination)
                        imported.append(name)

    return {'success': True, 'action': 'import', 'bundle': str(source), 'profile': profile,
            'platform': platform_tag, 'imported': imported, 'reused': reused}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('export', 'import'))
    parser.add_argument('--profile', choices=sorted(chain.PROFILES), required=True)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--library', action='append', default=[])
    args = parser.parse_args(argv)
    try:
        operation = export_cache if args.action == 'export' else import_cache
        result = operation(args.profile, args.library, args.bundle)
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
        result = {'success': False, 'action': args.action, 'error': str(exc)}
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
