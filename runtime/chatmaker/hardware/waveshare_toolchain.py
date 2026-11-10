"""Pinned, isolated Waveshare S3 toolchain; vendor sources are downloaded locally."""
from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
import platform
import tempfile
import zipfile

from chatmaker.installers.downloads import download_locked, sha256
from .esp32_devkit_v1 import _run as run

CORE_VERSION = '3.3.11'
PREPARATION_VERSION = 1
INDEX_URL = 'https://espressif.github.io/arduino-esp32/package_esp32_index.json'
CLI = {
    'filename': 'arduino-cli.zip', 'size': 17736240,
    'sha256': 'cfece6f356fdc9ca003cc3f0a488470030719c8e0e7bfce5e42ac9410d87441f',
    'sources': [{'id':'arduino-official','kind':'official_fallback',
                 'url':'https://github.com/arduino/arduino-cli/releases/download/v1.3.1/arduino-cli_1.3.1_Windows_64bit.zip'}],
}
VENDORS = {
    'v1': {'filename':'waveshare-v1.zip', 'size':93233319,
           'sha256':'db9fb7ebb8ef773cc1218658c6a2e3d8adc5bb3883e360256a3acb16d073a773',
           'sources':[{'id':'waveshare-cn','kind':'domestic_official','url':'https://files.waveshare.net/wiki/ESP32-S3-Touch-LCD-2.8/ESP32-S3-Touch-LCD-2.8-Demo.zip'}]},
    'v2': {'filename':'waveshare-v2.zip', 'size':94361713,
           'sha256':'b09e8cdfb47212ea94a06ba02a11568dfb70dcc1ea040142067d08e374b29737',
           'sources':[{'id':'waveshare-cn','kind':'domestic_official','url':'https://files.waveshare.net/wiki/ESP32-S3-Touch-LCD-2.8/ESP32-S3-Touch-LCD-2.8-V2-Demo.zip'}]},
}


def root() -> Path:
    return Path(os.environ.get('CHATMAKER_RUNTIME_ROOT', Path.cwd()/'.chatmaker-runtime')).resolve()/'toolchains'/'waveshare'


def file_manifest(directory: Path) -> dict[str, str]:
    return {p.relative_to(directory).as_posix(): sha256(p) for p in sorted(directory.rglob('*')) if p.is_file()}


def verify_manifest(directory: Path, manifest: dict, *, exact: bool = False) -> bool:
    if not isinstance(manifest, dict) or not manifest:
        return False
    try:
        if exact and set(manifest) != {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()}:
            return False
        for name, digest in manifest.items():
            relative = PurePosixPath(name)
            if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:
                return False
            path = directory / name
            if not path.is_file() or sha256(path) != digest:
                return False
        return True
    except (OSError, ValueError, TypeError):
        return False


def extract_vendor(archive: Path, libraries: Path, revision: str) -> None:
    if revision not in VENDORS:
        raise ValueError('revision_required')
    names = {'Display_ST7789.cpp','Display_ST7789.h','LVGL_Driver.cpp','LVGL_Driver.h',
             'Touch_CST328.h', 'Touch_CST328.cpp'}
    if revision == 'v2':
        names.update({'Touch_CST3530.h','Touch_CST3530.cpp'})
        names.remove('Touch_CST328.cpp')
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            name = info.filename
            rel = PurePosixPath(name)
            if rel.is_absolute() or '..' in rel.parts or '\\' in name or ':' in name:
                raise ValueError('unsafe_vendor_path')
            if info.is_dir():
                continue
            if name.startswith('Arduino/libraries/lvgl/'):
                destination = libraries/'lvgl'/name.removeprefix('Arduino/libraries/lvgl/')
                content = z.read(info)
            elif name.startswith('Arduino/examples/LVGL_Arduino/') and rel.name in names:
                destination = libraries/'WaveshareBoard'/'src'/rel.name
                content = z.read(info)
                if revision == 'v2' and rel.name in {'Display_ST7789.cpp','LVGL_Driver.cpp'}:
                    # Vendor V2 archive still invokes the V1 driver. Select the
                    # supplied CST3530 implementation without modifying user code.
                    content = content.replace(b'Touch_Init()', b'TOUCH2_Init()')
                    content = content.replace(b'Touch_Read_Data()', b'Touch2_Read_Data()')
                    content = content.replace(b'Touch_Get_XY(', b'Touch2_Get_XY(')
                    content = content.replace(b'CST328_LCD_TOUCH_MAX_POINTS', b'CST3530_LCD_TOUCH_MAX_POINTS')
            else:
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
    properties = libraries/'WaveshareBoard'/'library.properties'
    properties.parent.mkdir(parents=True, exist_ok=True)
    properties.write_text('name=WaveshareBoard\nversion=1.0.0\nauthor=Waveshare\nmaintainer=ChatMaker\nsentence=Locally prepared official Waveshare board drivers.\nparagraph=Revision-selected from verified official demo archive.\ncategory=Display\nurl=https://docs.waveshare.net/ESP32-S3-Touch-LCD-2.8/\narchitectures=esp32\n', encoding='utf-8')


def context(revision: str) -> dict | None:
    if revision not in VENDORS:
        return None
    home = root()
    revision_root = home/'revisions'/revision
    try:
        receipt = json.loads((revision_root/'receipt.json').read_text(encoding='utf-8'))
        if not isinstance(receipt, dict) or receipt.get('preparation_version') != PREPARATION_VERSION:
            return None
        if receipt.get('core_version') != CORE_VERSION or receipt.get('vendor_sha256') != VENDORS[revision]['sha256']:
            return None
        prepared_name = receipt.get('prepared_directory', '')
        if not isinstance(prepared_name, str) or not prepared_name.startswith('prepared-') or Path(prepared_name).name != prepared_name:
            return None
        prepared = revision_root/prepared_name
        if not verify_manifest(prepared/'libraries', receipt.get('files'), exact=True) or not verify_manifest(home, receipt.get('tools')):
            return None
        if not verify_manifest(prepared/'recovery', receipt.get('recovery_files'), exact=True):
            return None
        return {'root':str(home),'cli':str(home/'bin'/'arduino-cli.exe'),
                'config':str(home/'arduino-cli.yaml'),'libraries':str(prepared/'libraries'),
                'factory_recovery':receipt.get('recovery', []),
                'revision':revision,'backend':'chatmaker-managed-waveshare-s3'}
    except (OSError, ValueError, TypeError):
        return None


def prepare_environment(revision: str) -> dict:
    if revision not in VENDORS:
        return {'success':False,'state':'revision-needed','error':'revision_required'}
    if platform.system() != 'Windows' or platform.machine().lower() not in {'amd64','x86_64'}:
        return {'success':False,'error':'windows_x64_required'}
    ready = context(revision)
    if ready:
        return {'success':True,'ready_for_compile':True,'installation_performed':False,'environment':ready}
    home = root(); home.mkdir(parents=True, exist_ok=True)
    revision_root = home/'revisions'/revision
    receipt_path = revision_root/'receipt.json'
    try:
        # Preserve evidence of an altered/incomplete toolchain. Recreating a
        # receipt around damaged tools would incorrectly declare them healthy.
        if receipt_path.is_file():
            previous = json.loads(receipt_path.read_text(encoding='utf-8'))
            if isinstance(previous, dict) and previous.get('tools') and not verify_manifest(home, previous['tools']):
                return {'success':False,'error':'toolchain_cache_changed',
                        'teacher_message':'已准备的编译工具发生变化或缺失，已停止。请保留此缓存供检查，在新的 CHATMAKER_RUNTIME_ROOT 重新准备；不需要安装 Mind+。'}
        cli_zip = home/CLI['filename']
        download_locked(CLI,cli_zip,timeout=180)
        with zipfile.ZipFile(cli_zip) as z:
            (home/'bin').mkdir(exist_ok=True)
            (home/'bin'/'arduino-cli.exe').write_bytes(z.read('arduino-cli.exe'))
        config = {'directories':{key:str(home/value) for key,value in [('data','data'),('downloads','downloads'),('user','user')]},
                  'board_manager':{'additional_urls':[INDEX_URL]}}
        config_path = home/'arduino-cli.yaml'
        config_path.write_text(json.dumps(config,indent=2),encoding='utf-8')
        cli = [str(home/'bin'/'arduino-cli.exe'),'--config-file',str(config_path)]
        core = home/'data/packages/esp32/hardware/esp32'/CORE_VERSION
        if not (core/'boards.txt').is_file():
            for args in [('core','update-index'),('core','install',f'esp32:esp32@{CORE_VERSION}')]:
                step = run(cli+list(args),timeout=1200)
                if step.get('returncode') != 0:
                    return {'success':False,'error':'core_preparation_failed','execution':step,
                            'teacher_message':'乐鑫工具下载尚未完成；保留缓存，检查网络后重试这一步。'}
        details = run(cli+['board','details','--fqbn','esp32:esp32:esp32s3','--format','json'],timeout=60)
        if details.get('returncode') != 0:
            return {'success':False,'error':'exact_board_toolchain_unavailable','execution':details}
        vendor_zip = home/VENDORS[revision]['filename']
        download_locked(VENDORS[revision],vendor_zip,timeout=180)
        # Prepare into a fresh directory so stale sources cannot enter a new
        # manifest. Keep the previous files until a complete receipt is ready.
        revision_root.mkdir(parents=True, exist_ok=True)
        prepared = Path(tempfile.mkdtemp(prefix='prepared-', dir=revision_root))
        libraries = prepared/'libraries'
        extract_vendor(vendor_zip,libraries,revision)
        # Factory recovery images stay in the local cache with their source ZIP.
        recovery = []
        with zipfile.ZipFile(vendor_zip) as z:
            for name in z.namelist():
                if name.startswith('Firmware/') and name.lower().endswith('.bin') and '..' not in PurePosixPath(name).parts:
                    dst = prepared/'recovery'/PurePosixPath(name).name
                    dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(z.read(name))
                    recovery.append({'path':str(dst),'sha256':sha256(dst),'address':'0x0'})
        if not recovery:
            return {'success':False,'error':'factory_recovery_missing'}
        key_files = [home/'bin/arduino-cli.exe',config_path,core/'boards.txt',core/'platform.txt',
                     core/'cores/esp32/Arduino.h',core/'cores/esp32/main.cpp',
                     core/'variants/esp32s3/pins_arduino.h']
        # Do not recursively walk SDKs for other chips: Windows MAX_PATH is
        # exceeded by unrelated Matter headers even though S3 tools are usable.
        tools = home/'data/packages/esp32/tools'
        key_files += list(tools.glob('esp-x32/*/bin/xtensa-esp32s3-elf-g++.exe'))
        key_files += list(tools.glob('esptool_py/*/esptool.exe'))
        key_files += [tools/'esp32s3-libs'/CORE_VERSION/'sdkconfig']
        if not any(p.name.endswith('g++.exe') for p in key_files) or not any(p.name=='esptool.exe' for p in key_files):
            return {'success':False,'error':'compiler_or_flasher_missing'}
        receipt = {'preparation_version':PREPARATION_VERSION, 'prepared_directory':prepared.name,
                   'core_version':CORE_VERSION,'vendor_sha256':VENDORS[revision]['sha256'],
                   'files':file_manifest(libraries),'tools':{p.relative_to(home).as_posix():sha256(p) for p in key_files},
                   'recovery_files':file_manifest(prepared/'recovery'),
                   'recovery':recovery,'touch_controller':'CST328' if revision=='v1' else 'CST3530'}
        temporary_receipt = prepared/'receipt.json'
        temporary_receipt.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        temporary_receipt.replace(receipt_path)
        ready = context(revision)
        if not ready:
            return {'success':False,'error':'prepared_environment_not_verified'}
        return {'success':True,'ready_for_compile':True,'installation_performed':True,'environment':ready,
                'factory_recovery':recovery}
    except Exception as exc:
        return {'success':False,'error':'environment_preparation_failed','detail':str(exc),
                'teacher_message':'独立工具准备失败，已保留下载缓存；请根据详细错误继续，不需要安装 Mind+。'}
