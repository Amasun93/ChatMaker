"""Check the loaded ChatMaker files and update an official source checkout."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import tomllib
from urllib.request import Request, urlopen


SKILL = Path(__file__).resolve().parents[1]
REPOSITORIES = {
    'GitHub': ('https://github.com/Amasun93/ChatMaker', 'https://api.github.com/repos/Amasun93/ChatMaker'),
    'Gitee': ('https://gitee.com/amasun93/ChatMaker', 'https://gitee.com/api/v5/repos/amasun93/ChatMaker'),
}
SPECIALISTS = ('chatduino', 'chatweb', 'chatcad')
SKILL_FILE_TYPES = {'.md', '.py', '.yaml', '.yml', '.json'}
PACKAGE_INPUTS = ('pyproject.toml', 'distribution/core-runtime/requirements.lock')
TOOL_SETUP_INPUTS = {
    'runtime/chatmaker/installers/runtime_sources.json',
    'scripts/setup_local_runtime.ps1', 'scripts/setup_local_runtime.sh',
}
REVISION = re.compile(r'[0-9a-f]{40}')
REFRESH_PENDING = '.chatmaker-runtime-refresh-pending'
STARTUP_TTL = 24 * 60 * 60
STARTUP_RETRY = 15 * 60


def command(args, *, env=None, timeout=10):
    return subprocess.run(args, capture_output=True, encoding='utf-8', errors='replace',
                          env=env, timeout=timeout)


def git(root, *args, timeout=10):
    env = {key: value for key, value in os.environ.items()
           if key not in {'GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR', 'GIT_INDEX_FILE', 'GIT_NAMESPACE'}}
    env.update(GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='Never')
    return command(['git', '--no-optional-locks', '-C', str(root), *args], env=env, timeout=timeout)


def read_url(url):
    with urlopen(Request(url, headers={'User-Agent': 'ChatMaker-Version-Check'}), timeout=8) as response:
        data = response.read(4 * 1024 * 1024 + 1)
    if len(data) > 4 * 1024 * 1024:
        raise ValueError('remote_response_too_large')
    return data.decode('utf-8')


def package_version(text):
    value = tomllib.loads(text)['project']['version']
    if not isinstance(value, str) or not value:
        raise ValueError('invalid_version')
    return value


def official_target():
    for name, (repo, api) in REPOSITORIES.items():
        try:
            revision = json.loads(read_url(api + '/branches/main'))['commit']['sha']
            if not isinstance(revision, str) or not REVISION.fullmatch(revision):
                raise ValueError('invalid_revision')
            tree = json.loads(read_url(f'{api}/git/trees/{revision}?recursive=1'))
            if tree.get('truncated') is not False:
                raise ValueError('incomplete_source_tree')
            blobs = {item['path']: item['sha'] for item in tree['tree'] if item['type'] == 'blob'}
            if any(f'skills/{part}/SKILL.md' not in blobs for part in ('chatmaker', *SPECIALISTS)):
                raise ValueError('incomplete_skill_tree')
            raw = (f'https://raw.githubusercontent.com/Amasun93/ChatMaker/{revision}'
                   if name == 'GitHub' else f'{repo}/raw/{revision}')
            metadata = read_url(raw + '/pyproject.toml')
            if blob_hash(metadata.encode('utf-8')) != blobs['pyproject.toml']:
                raise ValueError('version_metadata_mismatch')
            return {'source': name, 'commit': revision, 'version': package_version(metadata),
                    'changelog': f'{repo}/blob/{revision}/WHATS_NEW.md'}, blobs
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            continue
    raise ValueError('official_update_sources_unavailable')


def blob_hash(data):
    # Compare file contents using Git's blob identifier from the commit tree.
    return hashlib.sha1(f'blob {len(data)}\0'.encode() + data, usedforsecurity=False).hexdigest()


def checkout_for_skill(skill):
    for directory in (skill, skill.resolve()):
        if directory.name == 'chatmaker' and directory.parent.name == 'skills':
            root = directory.parent.parent
            if (root / 'pyproject.toml').is_file():
                return root.resolve()
    return None


def skill_files(skill, root):
    folders = [(skill, 'chatmaker')]
    folders.extend(((root / 'skills' if root else skill / 'internal_skills') / part, part) for part in SPECIALISTS)
    for directory, part in folders:
        for file in directory.rglob('*'):
            if file.is_file() and file.suffix in SKILL_FILE_TYPES:
                relative = file.relative_to(directory)
                if relative.parts[0] != 'agents' and (part != 'chatmaker' or relative.parts[0] != 'internal_skills'):
                    yield f'skills/{part}/{relative.as_posix()}', file


def check_skill(skill, root, blobs):
    result = {'path': str(skill), 'version': None, 'source_commit': None, 'matches_target': None}
    if root:
        result['version'] = package_version((root / 'pyproject.toml').read_text(encoding='utf-8'))
        if (root / '.git').exists():
            try:
                head = git(root, 'rev-parse', 'HEAD')
                status = git(root, 'status', '--porcelain', '--', 'skills', 'pyproject.toml')
                if not head.returncode and not status.returncode and not status.stdout.strip():
                    result['source_commit'] = head.stdout.strip()
            except (OSError, subprocess.TimeoutExpired):
                pass  # File verification also works without Git.
    if blobs is not None:
        expected = {}
        for path, digest in blobs.items():
            parts = path.split('/')
            if (len(parts) >= 3 and parts[0] == 'skills' and parts[1] in ('chatmaker', *SPECIALISTS)
                    and Path(path).suffix in SKILL_FILE_TYPES and parts[2] != 'agents'):
                expected[path] = digest
        actual = {path: blob_hash(file.read_bytes().replace(b'\r\n', b'\n'))
                  for path, file in skill_files(skill, root)}
        result['matches_target'] = expected == actual
    return result


def inspect_runtime(runtime):
    if runtime is None:
        return {'status': 'not_checked'}
    fallback = {'status': 'runtime_check_failed', 'runtime_root': str(runtime)}
    pending = runtime / REFRESH_PENDING
    if pending.is_file():
        fallback.update(status='runtime_refresh_needed', source_root=pending.read_text(encoding='utf-8'))
    python = runtime / ('venv/Scripts/python.exe' if os.name == 'nt' else 'venv/bin/python3')
    if not python.is_file():
        return {**fallback, 'status': 'runtime_refresh_needed' if pending.is_file() else 'runtime_missing'}
    env = {**os.environ, 'CHATMAKER_RUNTIME_ROOT': str(runtime), 'GIT_OPTIONAL_LOCKS': '0'}
    try:
        check = command([str(python), '-I', '-B', '-m', 'chatmaker.hardware.workflow', '--version', '--progress', 'none'],
                        env=env, timeout=20)
        if check.returncode == 0:
            identity = json.loads(check.stdout)['runtime']
            status = 'runtime_refresh_needed' if pending.is_file() else 'checked'
            return {**identity, 'status': status}
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired):
        pass
    return fallback


def runtime_matches(runtime, target):
    if runtime['status'] == 'runtime_refresh_needed':
        return False
    if runtime['status'] != 'checked' or runtime.get('source_commit') is None or runtime.get('source_dirty') is not False:
        return None
    return runtime['source_commit'] == target['commit'] and runtime['installed_version'] == runtime['version'] == target['version']


def update_impact(root, revision, remote_blobs):
    unknown = {'scope': 'unknown'}
    if root is None or not revision or 'pyproject.toml' not in remote_blobs:
        return unknown
    try:
        result = git(root, 'ls-tree', '-r', '-z', revision)
    except (OSError, subprocess.TimeoutExpired):
        return unknown
    if result.returncode:
        return unknown

    local_blobs = {}
    for item in result.stdout.split('\0'):
        header, _, path = item.partition('\t')
        if path and header.split()[1] == 'blob':
            local_blobs[path] = header.rsplit(' ', 1)[-1]
    changed = {path for path in local_blobs.keys() | remote_blobs.keys()
               if local_blobs.get(path) != remote_blobs.get(path)}
    docs = {path for path in changed if path.startswith('docs/') or path in {
        'README.md', 'README_EN.md', 'WHATS_NEW.md', 'CONTRIBUTING.md',
    }}
    if changed == docs:
        scope = 'docs_only'
    elif all(path.startswith('skills/') for path in changed - docs):
        scope = 'skill_only'
    else:
        scope = 'project'
    return {
        'scope': scope,
        'changes_package_inputs': bool(changed.intersection(PACKAGE_INPUTS)),
        'changes_tool_setup': bool(changed.intersection(TOOL_SETUP_INPUTS)) or any(
            path.startswith('runtime/chatmaker/hardware/') and path.endswith('toolchain.py') for path in changed
        ),
    }


def official_main(root):
    if not (root / '.git').exists() or not (root / 'skills/chatmaker/SKILL.md').is_file():
        raise ValueError('source_checkout_required')
    origin = git(root, 'remote', 'get-url', 'origin')
    official = {repo.lower() for repo, _ in REPOSITORIES.values()}
    url = origin.stdout.strip().lower().rstrip('/').removesuffix('.git')
    for host in ('github.com', 'gitee.com'):
        for prefix in (f'git@{host}:', f'ssh://git@{host}/'):
            if url.startswith(prefix):
                url = f'https://{host}/' + url.removeprefix(prefix)
    if origin.returncode or url not in official:
        raise ValueError('official_chatmaker_origin_required')
    branch = git(root, 'symbolic-ref', '--quiet', '--short', 'HEAD')
    if branch.returncode or branch.stdout.strip() != 'main':
        raise ValueError('main_checkout_required')
    state = git(root, 'status', '--porcelain', '--untracked-files=all')
    if state.returncode or state.stdout.strip():
        raise ValueError('checkout_has_local_changes')
    head = git(root, 'rev-parse', 'HEAD')
    if head.returncode:
        raise ValueError('checkout_revision_unavailable')
    return head.stdout.strip()


@contextmanager
def checkout_lock(root):
    git_directory = git(root, 'rev-parse', '--absolute-git-dir')
    if git_directory.returncode:
        raise ValueError('source_checkout_required')
    lock = Path(git_directory.stdout.strip()) / 'chatmaker-update.lock'
    with lock.open('a+b') as handle:
        try:
            # Closing this handle releases the lock, including on interruption.
            if os.name == 'nt':
                import msvcrt

                if handle.tell() == 0:
                    handle.write(b'0')
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise ValueError('chatmaker_update_in_progress') from exc
        yield


def update_checkout(root, target, runtime, current_runtime):
    if not (root / '.git').exists():
        raise ValueError('source_checkout_required')
    with checkout_lock(root):
        return apply_update(root, target, runtime, current_runtime)


def apply_update(root, target, runtime, current_runtime):
    before = official_main(root)
    revision = target['commit']
    pending = runtime / REFRESH_PENDING if current_runtime.get('source_root') == str(root) else None
    if before != revision:
        shallow = git(root, 'rev-parse', '--is-shallow-repository').stdout.strip() == 'true'
        options = ('--unshallow',) if shallow else ()
        names = (target['source'], *(name for name in REPOSITORIES if name != target['source']))
        for name in names:
            repo, _ = REPOSITORIES[name]
            try:
                fetched = git(root, 'fetch', '--no-tags', '--no-recurse-submodules', *options,
                              repo + '.git', 'refs/heads/main', timeout=35)
            except subprocess.TimeoutExpired:
                continue
            if not fetched.returncode:
                options = ()
                if not git(root, 'merge-base', '--is-ancestor', revision, 'FETCH_HEAD').returncode:
                    break
        else:
            raise ValueError('target_revision_unavailable')
        if git(root, 'merge-base', '--is-ancestor', before, revision).returncode:
            raise ValueError('checkout_has_local_commits_or_mirror_is_older')
        if official_main(root) != before:
            raise ValueError('checkout_changed_during_update')
        if pending and git(root, 'diff', '--quiet', before, revision, '--', *PACKAGE_INPUTS).returncode != 0:
            pending.write_text(str(root), encoding='utf-8')
        merged = git(root, 'merge', '--ff-only', '--no-autostash', '--no-overwrite-ignore', revision, timeout=30)
        if merged.returncode:
            raise ValueError('source_update_failed')

    # An editable runtime sees new source on the next invocation. Reinstall its
    # metadata or dependencies when they changed, and recheck the actual runtime.
    after = inspect_runtime(runtime)
    if pending and not runtime_matches(after, target):
        pending.write_text(str(root), encoding='utf-8')
        if os.name == 'nt':
            setup = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                     str(root / 'scripts/setup_local_runtime.ps1'), '-SourceRoot', str(root), '-RuntimeRoot', str(runtime)]
        else:
            setup = ['bash', str(root / 'scripts/setup_local_runtime.sh')]
        env = {**os.environ, 'CHATMAKER_RUNTIME_ROOT': str(runtime)}
        try:
            if command(setup, env=env, timeout=360).returncode == 0:
                pending.unlink(missing_ok=True)
                return before != revision, inspect_runtime(runtime)
        except (OSError, subprocess.TimeoutExpired):
            pass
        after = {**after, 'status': 'runtime_refresh_failed'}
    return before != revision, after


def startup_cache(args):
    if os.name == 'nt':
        base = Path(os.environ.get('LOCALAPPDATA') or Path.home() / 'AppData/Local')
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library/Caches'
    else:
        base = Path(os.environ.get('XDG_CACHE_HOME') or Path.home() / '.cache')
    paths = [str(path.expanduser().absolute()) if path else '' for path in
             (args.skill_dir, args.checkout, args.runtime_root)]
    fingerprint = hashlib.sha256(json.dumps(paths).encode()).hexdigest()[:24]
    return base / 'ChatMaker' / 'version-check' / f'{fingerprint}.json'


def save_startup(cache, report):
    cache.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=cache.parent, delete=False, mode='w', encoding='utf-8') as handle:
        temporary = Path(handle.name)
        json.dump({**report, 'checked_at': time.time()}, handle)
    try:
        temporary.replace(cache)
    finally:
        temporary.unlink(missing_ok=True)


def startup(args):
    cache = startup_cache(args)
    skill = args.skill_dir.expanduser().absolute()
    skill_stamp = []
    for path in (skill / 'SKILL.md', skill / 'scripts/chatmaker_version.py'):
        try:
            info = path.stat()
            skill_stamp.append([info.st_mtime_ns, info.st_size])
        except FileNotFoundError:
            skill_stamp.append(None)
    if args.action == '_startup-worker':
        try:
            report = run(argparse.Namespace(**{**vars(args), 'action': 'check-update'}))
            root = checkout_for_skill(skill)
            if report.get('update_available') and root and (root / '.git').exists():
                # A dirty checkout or a lagging mirror is not a newer release.
                head = git(root, 'rev-parse', 'HEAD')
                target = report['target']['commit']
                if not head.returncode and (head.stdout.strip() == target or
                                            not git(root, 'merge-base', '--is-ancestor', target, 'HEAD').returncode):
                    report.update(status='no_newer_source', update_available=False)
                    report.pop('update_impact', None)
        except (OSError, ValueError, KeyError, subprocess.SubprocessError):
            report = {'success': False, 'status': 'startup_check_unavailable', 'update_available': None}
        save_startup(cache, {**report, 'skill_stamp': skill_stamp})
        return report

    empty = {'success': True, 'status': 'startup_check_not_run', 'update_available': None}
    try:
        cached = json.loads(cache.read_text(encoding='utf-8'))
        ttl = STARTUP_TTL if cached['status'] in {'update_checked', 'no_newer_source'} else STARTUP_RETRY
        if cached['status'] == 'startup_check_pending':
            ttl = 120
        if cached.get('skill_stamp') == skill_stamp and 0 <= time.time() - cached['checked_at'] < ttl:
            return {**cached, 'success': True}
    except (OSError, ValueError, KeyError, TypeError):
        pass
    if args.action == 'startup-status':
        return empty

    worker = [sys.executable, '-I', '-B', str(Path(__file__).resolve()), '_startup-worker']
    for name, path in (('--skill-dir', args.skill_dir), ('--checkout', args.checkout),
                       ('--runtime-root', args.runtime_root)):
        if path:
            worker.extend((name, str(path.expanduser().absolute())))
    pending = {**empty, 'status': 'startup_check_pending'}
    detached = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {'start_new_session': True}
    try:
        save_startup(cache, {**pending, 'skill_stamp': skill_stamp})
        subprocess.Popen(worker, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, **detached)
    except OSError:
        return {**empty, 'status': 'startup_check_unavailable'}
    return pending


def run(args):
    if args.action in {'startup-check', 'startup-status', '_startup-worker'}:
        return startup(args)
    # Keep the host-visible path so separate Skill directory links stay visible.
    skill = args.skill_dir.expanduser().absolute()
    if not (skill / 'SKILL.md').is_file():
        return {'action': args.action, 'success': False, 'status': 'skill_files_unavailable',
                'skill': {'path': str(skill)}}
    skill_root = checkout_for_skill(skill)
    root = args.checkout.expanduser().resolve() if args.checkout else skill_root
    runtime = args.runtime_root.expanduser().resolve() if args.runtime_root else None
    if runtime is None and root:
        project_runtime = root / '.chatmaker-runtime'
        if (project_runtime / 'venv').exists() or (project_runtime / REFRESH_PENDING).exists():
            runtime = project_runtime
    local_runtime = inspect_runtime(runtime)
    if root is None and (local_runtime.get('source_commit') or local_runtime['status'] == 'runtime_refresh_needed'):
        root = Path(local_runtime['source_root'])
    report = {'action': args.action, 'skill': check_skill(skill, skill_root, None), 'runtime': local_runtime}
    if args.action == 'self-check':
        return {**report, 'success': True, 'status': 'local_check'}
    try:
        target, blobs = official_target()
    except ValueError as exc:
        return {**report, 'success': False, 'status': str(exc), 'update_available': None}
    report['target'] = target
    if args.action == 'update' and root is not None:
        try:
            changed, local_runtime = update_checkout(root, target, runtime, local_runtime)
        except ValueError as exc:
            return {**report, 'success': False, 'status': str(exc), 'update_available': None}
        except (OSError, subprocess.SubprocessError):
            return {**report, 'success': False, 'status': 'source_update_failed', 'update_available': None}
        report['source_updated'] = changed
        report['reload_required'] = changed and (skill_root is not None and skill_root == root)
    report['skill'] = check_skill(skill, skill_root, blobs)
    if report['skill']['matches_target']:
        report['skill']['version'] = target['version']
        report['skill']['verified_against_commit'] = target['commit']
    report['runtime'] = {**local_runtime, 'matches_target': runtime_matches(local_runtime, target)}
    skill_match = report['skill']['matches_target']
    runtime_match = report['runtime']['matches_target']
    report['update_available'] = (True if False in (skill_match, runtime_match) else
                                  False if skill_match is True and (runtime_match is True or runtime is None) else None)
    if args.action == 'check-update' and report['update_available']:
        report['update_impact'] = update_impact(skill_root, report['skill']['source_commit'], blobs)
    if args.action == 'update':
        if skill_match is not True and (skill_root is None or skill_root != root):
            return {**report, 'success': False, 'status': 'host_skill_update_required'}
        if runtime is not None and runtime_match is not True:
            return {**report, 'success': False, 'status': 'runtime_verification_needed'}
        if skill_match is not True:
            return {**report, 'success': False, 'status': 'skill_verification_needed'}
        status = 'updated' if report.get('source_updated') else 'current'
        try:
            startup_cache(args).unlink(missing_ok=True)
        except OSError:
            pass
        return {**report, 'success': True, 'status': status}
    return {**report, 'success': True, 'status': 'update_checked'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('self-check', 'check-update', 'update',
                                          'startup-check', 'startup-status', '_startup-worker'))
    parser.add_argument('--skill-dir', type=Path, default=SKILL)
    parser.add_argument('--checkout', type=Path, help='ChatMaker source directory, when separate from the loaded Skill')
    parser.add_argument('--runtime-root', type=Path, help='Runtime directory of the tool this session uses')
    try:
        report = run(parser.parse_args())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        report = {'success': False, 'status': str(exc)}
    print(json.dumps(report, ensure_ascii=True))
    return 0 if report['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
