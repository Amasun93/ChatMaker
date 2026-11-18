"""Explicit ESP32 classroom profiles with isolated compilation and upload."""
from pathlib import Path
import time

from . import arduino_toolchain as chain
from .esp32_devkit_v1 import port_matches, scan_ports
from .arduino_toolchain import run_cli as run
from .classroom_cli import dry_run_guard
from .waveshare_s3 import compile_project, match_application_port
from chatmaker.progress import emit

PROFILES = {
    'esp32-devkit-v1': ('esp32', 'esp32:esp32:esp32doit-devkit-v1'),
    'nova-esp32': ('esp32', 'esp32:esp32:esp32:FlashSize=4M,FlashMode=dio,PartitionScheme=default'),
    'esp32-s3-devkitc-1-n8r8': ('esp32s3', 'esp32:esp32:esp32s3:FlashSize=8M,PSRAM=opi,PartitionScheme=default_8MB,USBMode=hwcdc'),
    'esp32-c3-devkitm-1': ('esp32c3', 'esp32:esp32:esp32c3:FlashSize=4M'),
    'esp32-c6-devkitc-1': ('esp32c6', 'esp32:esp32:esp32c6:FlashSize=8M,PartitionScheme=default_8MB'),
    'seeed-xiao-esp32s3': ('esp32s3', 'esp32:esp32:XIAO_ESP32S3:PSRAM=opi,USBMode=hwcdc,CDCOnBoot=default'),
    'seeed-xiao-esp32s3-sense': ('esp32s3', 'esp32:esp32:XIAO_ESP32S3:PSRAM=opi,USBMode=hwcdc,CDCOnBoot=default'),
    'unihiker-k10': ('unihiker_k10', 'UNIHIKER:esp32:k10:PSRAM=opi,USBMode=hwcdc,CDCOnBoot=cdc'),
}
XIAO_BOARDS = {'seeed-xiao-esp32s3', 'seeed-xiao-esp32s3-sense'}
NATIVE_ONLY = XIAO_BOARDS | {'unihiker-k10'}


def requested_libraries(request):
    libraries = list(request.get('libraries') or [])
    source = str(request.get('code', ''))
    if request.get('sketch'):
        path = Path(request['sketch']).expanduser()
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
    profile, fqbn = PROFILES[board_id]
    # Boards with both USB-UART and native USB need the serial route selected
    # before compiling. Arduino's Serial follows the CDC-on-boot setting.
    fixed_native = board_id in NATIVE_ONLY
    supported_modes = (None, 'native') if fixed_native else (None, 'uart')
    dual_usb = not fixed_native and profile in {'esp32s3', 'esp32c6'}
    if dual_usb:
        supported_modes += ('native',)
    if request.get('usb_mode') not in supported_modes:
        return {**base, 'error': 'unsupported_usb_mode'}
    native_usb = fixed_native or request.get('usb_mode') == 'native'
    if dual_usb and native_usb:
        fqbn += ',CDCOnBoot=cdc'
    libraries = requested_libraries(request)
    if action == 'prepare-environment':
        return {**base, **chain.prepare(profile, libraries=libraries, dry_run=request.get('dry_run') is True)}
    if action == 'ports':
        return {**base, 'success': True, 'ports': scan_ports()}
    ctx = chain.context(profile, libraries=libraries)
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
    diagnostic = compiled.get('execution', {}).get('stderr', '')
    if not compiled['success'] and profile in {'esp32c3', 'esp32c6'} and ctx.get('platform') == 'windows-amd64' and any(
            f'bits/{header}: No such file or directory' in diagnostic for header in ('c++config.h', 'error_constants.h')):
        result.update(error='compiler_path_too_long', teacher_message='这个 Windows 编译器在较长的目录中找不到头文件。请把 CHATMAKER_RUNTIME_ROOT 指到较短的本地路径，再准备当前板型。')
    if not compiled['success'] or action == 'compile':
        return result
    if request.get('board_confirmed') is not True:
        return {**result, 'success': False, 'stage': 'identity', 'error': 'board_identity_required',
                'teacher_message': '请确认本次连接的板型和模块规格。USB 串口只用于选择下载目标。'}

    def eligible(port):
        if port.get('is_bluetooth'):
            return False
        if board_id in XIAO_BOARDS and (port.get('vid'), port.get('pid')) == (0x2886, 0x0056):
            return True
        return port.get('vid') == 0x303A if native_usb else port.get('usb_uart_likely')

    ports = [port for port in scan_ports() if eligible(port)]
    if request.get('port'):
        ports = [p for p in ports if port_matches(p['address'], request['port'])]
    elif fixed_native and (len(ports) != 1 or ports[0].get('vid') == 0x303A):
        return {**result, 'success': False, 'stage': 'awaiting-hardware', 'ports': ports,
                'teacher_message': '请拔插目标板，找出随它消失和重新出现的端口，再选这个端口下载。'}
    if len(ports) != 1:
        return {**result, 'success': False, 'stage': 'awaiting-hardware', 'ports': ports,
                'teacher_message': '程序已编译，请连接数据线并选择本次使用的 USB 串口。'}
    port = ports[0]['address']
    emit('stage', stage='upload', component=board_id, message='正在下载程序到已确认的板子')
    execution = run([ctx['cli'], '--config-file', ctx['config'], 'upload', '--fqbn', fqbn,
                     '--port', port, '--input-dir', compiled.get('artifact_dir', compiled['build_path']), compiled['sketch']],
                    timeout=int(request.get('upload_timeout', 180)))
    application_port = None if native_usb else port
    if native_usb and execution.get('returncode') == 0:
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            application_port = match_application_port(ports[0], scan_ports(), eligible=eligible)
            if application_port:
                break
            time.sleep(0.25)
    upload = {'success': execution.get('returncode') == 0, 'port': port,
              'application_port': application_port, 'execution': execution}
    return {**result, 'success': upload['success'], 'upload': upload,
            'stage': 'complete' if upload['success'] else 'upload'}
