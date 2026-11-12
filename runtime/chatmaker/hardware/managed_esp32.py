"""Explicit classic ESP32 classroom profiles with isolated compilation and upload."""
from pathlib import Path

from . import arduino_toolchain as chain
from .esp32_devkit_v1 import scan_ports
from .arduino_toolchain import run_cli as run
from .classroom_cli import dry_run_guard
from .waveshare_s3 import compile_project
from chatmaker.progress import emit

PROFILES = {
    'esp32-devkit-v1': 'esp32:esp32:esp32doit-devkit-v1',
    'nova-esp32': 'esp32:esp32:esp32:FlashSize=4M,FlashMode=dio,PartitionScheme=default',
}


def requested_libraries(request):
    libraries = list(request.get('libraries') or [])
    source = str(request.get('code', ''))
    if request.get('sketch'):
        path = Path(request['sketch'])
        files = [path] if path.is_file() else path.glob('*.ino')
        source += '\n'.join(p.read_text(encoding='utf-8-sig') for p in files)
    if 'U8g2lib.h' in source and 'U8g2' not in libraries:
        libraries.append('U8g2')
    return libraries


def execute_request(request: dict) -> dict:
    board_id = request.get('board_id', 'esp32-devkit-v1')
    action = request.get('action', 'doctor')
    base = {'success': False, 'action': action, 'board': board_id, 'physical_effect_verified': False}
    rejected = dry_run_guard(request, default_action='doctor')
    if rejected:
        return {**base, **rejected}
    if board_id not in PROFILES:
        return {**base, 'error': 'unsupported_board'}
    fqbn = PROFILES[board_id]
    libraries = requested_libraries(request)
    if action == 'prepare-environment':
        return {**base, **chain.prepare('esp32', libraries=libraries, dry_run=request.get('dry_run') is True)}
    if action == 'ports':
        return {**base, 'success': True, 'ports': scan_ports()}
    ctx = chain.context('esp32', libraries=libraries)
    if action == 'doctor':
        return {**base, 'success': ctx is not None, 'ready_for_compile': ctx is not None,
                'installation_performed': False, 'error': None if ctx else 'exact_esp32_toolchain_missing',
                'environment': ctx, 'required_fqbn': fqbn, 'next_action': None if ctx else 'prepare-environment'}
    if action not in {'compile', 'compile-upload'}:
        return {**base, 'error': 'unsupported_action'}
    if ctx is None:
        return {**base, 'error': 'managed_toolchain_missing', 'next_action': 'prepare-environment'}
    compiled = compile_project({**request, 'revision': None}, ctx, fqbn=fqbn)
    result = {**base, 'success': compiled['success'], 'stage': 'compile', 'compile': compiled}
    if not compiled['success'] or action == 'compile':
        return result
    if request.get('board_confirmed') is not True:
        return {**result, 'success': False, 'stage': 'identity', 'error': 'board_identity_required',
                'teacher_message': '请确认本次连接的板型；CH340 串口不能单独证明是 Nova 或 DOIT。'}
    ports = [p for p in scan_ports() if p.get('usb_uart_likely') and not p.get('is_bluetooth')]
    if request.get('port'):
        ports = [p for p in ports if p['address'].casefold() == str(request['port']).casefold()]
    if len(ports) != 1:
        return {**result, 'success': False, 'stage': 'awaiting-hardware', 'ports': ports,
                'teacher_message': '程序已编译，请连接数据线并选择本次使用的 USB 串口。'}
    port = ports[0]['address']
    emit('stage', stage='upload', component=board_id, message='正在下载程序到已确认的板子')
    execution = run([ctx['cli'], '--config-file', ctx['config'], 'upload', '--fqbn', fqbn,
                     '--port', port, '--input-dir', compiled['build_path'], compiled['sketch']],
                    timeout=int(request.get('upload_timeout', 180)))
    upload = {'success': execution.get('returncode') == 0, 'port': port, 'application_port': port, 'execution': execution}
    return {**result, 'success': upload['success'], 'upload': upload,
            'stage': 'complete' if upload['success'] else 'upload'}
