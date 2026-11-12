"""Shell-safe common classroom arguments and source revision guards."""
import argparse
import json
import os
from pathlib import Path
import sys

from chatmaker.progress import reporting
from chatmaker.runtime_info import identity


def dry_run_guard(request, *, default_action=None):
    if request.get('dry_run') is True and request.get('action', default_action) not in {
            'prepare-environment', 'doctor', 'ports'}:
        return {'success': False, 'state': 'request-failed', 'error': 'dry_run_unsupported_action',
                'installation_performed': False, 'physical_effect_verified': False,
                'teacher_message': '试运行仅支持环境准备计划、环境检查或端口查询；此动作没有执行。'}
    return None


def main_entry(handler, argv=None, *, board_id=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument('--request-json', help="JSON object, or '-' to read stdin")
    inputs.add_argument('--request-file', help='UTF-8 JSON file (Windows BOM supported)')
    for name in ('action', 'board-id', 'revision', 'sketch', 'port', 'expect-revision', 'expect-source-root'):
        parser.add_argument('--' + name)
    parser.add_argument('--board-confirmed', action='store_true', default=None)
    parser.add_argument('--library', action='append', dest='libraries')
    parser.add_argument('--dry-run', action='store_true', default=None)
    parser.add_argument('--version', action='store_true')
    parser.add_argument('--progress', choices=('human', 'jsonl', 'none'), default='human')
    parser.add_argument('--download-policy', choices=('domestic-first', 'domestic-only'))
    args = parser.parse_args(argv)
    info = identity()
    policy_before = os.environ.get('CHATMAKER_DOWNLOAD_POLICY')
    try:
        if args.expect_revision and info['source_commit'] != args.expect_revision:
            raise ValueError('source_revision_mismatch')
        if args.expect_source_root and Path(args.expect_source_root).resolve() != Path(info['source_root']):
            raise ValueError('source_root_mismatch')
        if args.version:
            result = {'success': True, 'action': 'version'}
        else:
            request = {}
            if args.request_file:
                request = json.loads(Path(args.request_file).read_text(encoding='utf-8-sig'))
            elif args.request_json:
                request = json.loads(sys.stdin.read().lstrip('\ufeff') if args.request_json == '-' else args.request_json)
            if not isinstance(request, dict):
                raise ValueError('request_must_be_object')
            for name in ('action', 'board_id', 'revision', 'sketch', 'port', 'board_confirmed', 'dry_run', 'libraries'):
                value = getattr(args, name)
                if value is not None:
                    request[name] = value
            if board_id:
                request['board_id'] = board_id
            rejected = dry_run_guard(request)
            if rejected:
                raise ValueError(rejected['error'])
            if args.download_policy:
                os.environ['CHATMAKER_DOWNLOAD_POLICY'] = args.download_policy
            # Independent of the caller's working directory or another C: clone.
            os.environ.setdefault('CHATMAKER_RUNTIME_ROOT', info['runtime_root'])
            with reporting(args.progress):
                result = handler(request)
    except Exception as exc:
        result = {'success': False, 'state': 'request-failed', 'error': str(exc),
                  'installation_performed': False}
    finally:
        if policy_before is None:
            os.environ.pop('CHATMAKER_DOWNLOAD_POLICY', None)
        else:
            os.environ['CHATMAKER_DOWNLOAD_POLICY'] = policy_before
    result['runtime'] = info
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result.get('success') else 1
