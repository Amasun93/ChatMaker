"""One board-aware local execution path for independently managed Arduino boards."""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from typing import Any, Mapping


MODULES = {
    'idmc-0001-starcore-v4-2-2': 'starcore',
    'mpython-classic-v2x': 'mpython_classic',
    'mpython-v3': 'mpython_v3',
    'esp32-devkit-v1': 'esp32_devkit_v1',
    'waveshare-esp32-s3-touch-lcd-2-8': 'waveshare_s3',
}


def _observe(port: str, marker: str, baudrate: int, timeout: float) -> dict:
    from .serial_monitor import SERIAL_MANAGER
    opened = SERIAL_MANAGER.open(port, baudrate=baudrate, timeout=0.1)
    if not opened.get('success'):
        return opened
    try:
        return SERIAL_MANAGER.expect(opened['session_id'], marker, timeout=timeout, max_lines=300)
    finally:
        SERIAL_MANAGER.close(opened['session_id'])


def run_project(request: dict, *, adapters: Mapping[str, Any] | None = None) -> dict:
    board_id = str(request.get('board_id', ''))
    result = {'action': 'hardware-project-run', 'board_id': board_id, 'success': False,
              'code_compiled': False, 'firmware_uploaded': False, 'physical_effect_verified': False}
    if adapters is None:
        adapters = {board_id: importlib.import_module(f'.{MODULES[board_id]}', __package__)} if board_id in MODULES else {}
    adapter = adapters.get(board_id)
    if adapter is None:
        return {**result, 'state': 'unsupported-board', 'supported_boards': sorted(MODULES),
                'teacher_message': '这块板尚未接入此独立运行入口，请使用它自己的已验证路线。'}
    action = request.get('action', 'run')
    if action != 'run':
        if action not in {'doctor', 'prepare-environment', 'compile', 'compile-upload', 'ports'}:
            return {**result, 'state': 'unsupported-action', 'error': 'unsupported_action'}
        return {**adapter.execute_request(request), 'board_id': board_id}
    if not request.get('code') and not request.get('sketch'):
        return {**result, 'state': 'source-needed', 'teacher_message': '先保存这个作品的完整程序。'}
    doctor = adapter.execute_request({**request, 'action': 'doctor'})
    if doctor.get('state') == 'revision-needed':
        return {**result, 'state': 'revision-needed', 'environment': doctor,
                'teacher_message': doctor.get('teacher_message')}
    if not doctor.get('ready_for_compile'):
        prepared = adapter.execute_request({**request, 'action': 'prepare-environment'})
        result['environment'] = prepared
        if not prepared.get('success'):
            return {**result, 'state': 'awaiting-environment',
                    'teacher_message': prepared.get('teacher_message', '必要工具尚未准备完成，请按这次失败信息继续排查；保留已经生成的程序。')}
    execution = adapter.execute_request({**request, 'action': 'compile-upload'})
    result['execution'] = execution
    # Existing adapters return either a nested compile result (with upload=None
    # on failure), or the standalone compile result when compilation stops.
    compiled = execution.get('compile') or (execution if execution.get('action') == 'compile' else {})
    upload = execution.get('upload') or {}
    result['code_compiled'] = bool(compiled.get('success'))
    result['firmware_uploaded'] = bool(upload.get('success'))
    if not execution.get('success') or not result['firmware_uploaded']:
        stage = execution.get('stage') or ('compile' if execution.get('action') == 'compile' else None)
        state = 'compiled-awaiting-hardware' if stage == 'awaiting-hardware' else 'compile-failed' if stage == 'compile' else 'upload-needs-attention'
        return {**result, 'state': state, 'teacher_message': execution.get('teacher_message', '请查看当前步骤的检查结果，程序和已完成步骤会保留。')}
    result['success'] = True
    result['state'] = 'uploaded-awaiting-observation'
    port = upload.get('application_port', upload.get('port'))
    marker = request.get('expected_serial_marker')
    if port and marker:
        try:
            observation = _observe(str(port), str(marker), int(request.get('serial_baudrate', 115200)), float(request.get('serial_timeout', 10)))
        except Exception as exc:
            observation = {'success': False, 'error': str(exc)}
        result['serial_evidence'] = observation
        if observation.get('matched'):
            result['state'] = 'runtime-observed'
    result['teacher_message'] = '程序已下载。请检查屏幕、触摸或其他实物效果。'
    return result


def main(argv: list[str] | None = None) -> int:
    from .classroom_cli import main_entry
    return main_entry(run_project, argv)


if __name__ == '__main__':
    raise SystemExit(main())
