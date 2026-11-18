"""Managed Arduino Uno, classic Nano and Mega boards."""

from . import arduino_toolchain as chain
from .classroom_cli import dry_run_guard
from .esp32_devkit_v1 import port_matches, scan_ports
from .managed_esp32 import requested_libraries
from .nano_mindplus import _upload_diagnostics
from .waveshare_s3 import compile_project
from chatmaker.progress import emit

FQBNS = {
    'arduino-uno-r3': 'arduino:avr:uno',
    'arduino-nano-classic': 'arduino:avr:nano:cpu=atmega328',
    'arduino-mega-2560': 'arduino:avr:mega:cpu=atmega2560',
    'arduino-uno-r4-wifi': 'arduino:renesas_uno:unor4wifi',
}
ARDUINO_USB_IDS = {
    'arduino-uno-r3': {(0x2341, 0x0043), (0x2341, 0x0001), (0x2A03, 0x0043),
                      (0x2341, 0x0243), (0x2341, 0x006A)},
    'arduino-nano-classic': {(0x2341, 0x0058)},
    'arduino-mega-2560': {(0x2341, 0x0010), (0x2341, 0x0042), (0x2A03, 0x0010),
                         (0x2A03, 0x0042), (0x2341, 0x0210), (0x2341, 0x0242)},
    'arduino-uno-r4-wifi': {(0x2341, 0x1002), (0x2341, 0x006D)},
}


def execute_request(request: dict) -> dict:
    board = request.get('board_id')
    action = request.get('action', 'doctor')
    result = {'success': False, 'action': action, 'board': board, 'physical_effect_verified': False}
    rejected = dry_run_guard(request, default_action='doctor')
    if rejected:
        return {**result, **rejected}
    if board not in FQBNS:
        return {**result, 'error': 'unsupported_board'}

    bootloader = request.get('bootloader')
    if board == 'arduino-nano-classic' and bootloader not in (None, 'old', 'new'):
        return {**result, 'error': 'unsupported_nano_bootloader'}
    fqbn = FQBNS[board]
    if board == 'arduino-nano-classic' and bootloader == 'old':
        fqbn = 'arduino:avr:nano:cpu=atmega328old'
    renesas = board == 'arduino-uno-r4-wifi'
    profile = 'renesas_uno' if renesas else 'avr'
    libraries = requested_libraries(request)
    if action == 'prepare-environment':
        return {**result, **chain.prepare(profile, libraries=libraries, dry_run=request.get('dry_run') is True)}
    if action == 'ports':
        return {**result, 'success': True, 'ports': scan_ports()}
    context = chain.context(profile, libraries=libraries)
    if action == 'doctor':
        return {**result, 'success': context is not None, 'ready_for_compile': context is not None,
                'installation_performed': False, 'required_fqbn': fqbn, 'environment': context,
                'next_action': None if context else 'prepare-environment'}
    if action not in {'compile', 'compile-upload'}:
        return {**result, 'error': 'unsupported_action'}
    if context is None:
        return {**result, 'error': 'managed_toolchain_missing', 'next_action': 'prepare-environment'}

    compiled = compile_project(request, context, fqbn=fqbn, output_suffix='bin' if renesas else 'hex')
    result.update(success=compiled['success'], stage='compile', compile=compiled)
    if not compiled['success'] or action == 'compile':
        return result
    if request.get('board_confirmed') is not True:
        return {**result, 'success': False, 'stage': 'identity', 'error': 'board_identity_required',
                'teacher_message': '请确认本次连接的 Arduino 板型，再下载程序。'}
    ports = [port for port in scan_ports() if not port['is_bluetooth'] and
             ((port.get('vid'), port.get('pid')) in ARDUINO_USB_IDS[board]
              or (not renesas and port['usb_uart_likely']))]
    if request.get('port'):
        ports = [port for port in ports if port_matches(port['address'], request['port'])]
    if len(ports) != 1:
        return {**result, 'success': False, 'stage': 'awaiting-hardware', 'ports': ports,
                'teacher_message': '程序已编译，请选择本次使用的 Arduino USB 串口。'}
    selected = ports[0]
    port = selected['address']
    emit('stage', stage='upload', component=board, message='正在下载程序到已确认的板子')
    upload_targets = [fqbn]
    if board == 'arduino-nano-classic' and bootloader is None:
        # The two Nano definitions target the same MCU and application layout.
        upload_targets.append('arduino:avr:nano:cpu=atmega328old')
    attempts = []
    for attempt, target in enumerate(upload_targets):
        if attempt and not any(
                port_matches(row['address'], port) and not row['is_bluetooth']
                and all(not selected.get(field) or row.get(field) == selected[field]
                        for field in ('vid', 'pid', 'serial_number', 'location'))
                for row in scan_ports()):
            break
        execution = chain.run_cli([context['cli'], '--config-file', context['config'], 'upload', '--fqbn', target,
                                   '--port', port, '--input-dir', compiled.get('artifact_dir', compiled['build_path']), compiled['sketch']],
                                  timeout=int(request.get('upload_timeout', 180)))
        attempts.append(execution)
        if execution.get('returncode') == 0 or execution.get('timed_out'):
            break
        if _upload_diagnostics(execution)['error_type'] != 'bootloader_sync_failed':
            break
    success = execution.get('returncode') == 0
    return {**result, 'success': success, 'stage': 'complete' if success else 'upload',
            'upload': {'success': success, 'port': port, 'application_port': port, 'execution': execution,
                       'attempts': attempts}}
