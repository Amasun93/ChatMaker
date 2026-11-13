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
from . import arduino_toolchain as managed
from chatmaker.progress import emit

CORE_VERSION = '3.3.11'
PREPARATION_VERSION = 3
CORE_TREE = f'data/packages/esp32/hardware/esp32/{CORE_VERSION}'
COMPILER_TREE = 'data/packages/esp32/tools/esp-x32/2601'
SDK_TREE = f'data/packages/esp32/tools/esp32s3-libs/{CORE_VERSION}'
FLASHER_TREE = 'data/packages/esp32/tools/esptool_py/5.3.1'
TOOL_TREES = (CORE_TREE, COMPILER_TREE, SDK_TREE, FLASHER_TREE, 'data/packages/builtin/tools')
REQUIRED_TOOL_FILES = (
    'bin/arduino-cli.exe', 'arduino-cli.yaml',
    f'{CORE_TREE}/boards.txt', f'{CORE_TREE}/platform.txt',
    f'{CORE_TREE}/cores/esp32/Arduino.h', f'{CORE_TREE}/cores/esp32/main.cpp',
    f'{CORE_TREE}/cores/esp32/HardwareSerial.cpp', f'{CORE_TREE}/variants/esp32s3/pins_arduino.h',
    f'{COMPILER_TREE}/bin/xtensa-esp32s3-elf-gcc.exe',
    f'{COMPILER_TREE}/bin/xtensa-esp32s3-elf-g++.exe',
    f'{COMPILER_TREE}/bin/xtensa-esp32s3-elf-ld.exe',
    f'{COMPILER_TREE}/libexec/gcc/xtensa-esp-elf/14.2.0/cc1.exe',
    f'{COMPILER_TREE}/libexec/gcc/xtensa-esp-elf/14.2.0/cc1plus.exe',
    f'{SDK_TREE}/sdkconfig', f'{FLASHER_TREE}/esptool.exe',
    'data/packages/builtin/tools/ctags/5.8-arduino11/ctags.exe',
)
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
    return managed.home_for('esp32s3')


def configuration(home: Path) -> dict:
    return managed.configuration(home)


def config_matches(home: Path) -> bool:
    try:
        return json.loads((home/'arduino-cli.yaml').read_text(encoding='utf-8')) == configuration(home)
    except (OSError, ValueError):
        return False


def _filesystem_path(path: Path) -> Path:
    # SDK headers can exceed MAX_PATH. Use the native Windows extended form
    # only for our file operations; CLI arguments and receipts stay portable.
    if os.name != 'nt':
        return path
    value = str(path.absolute())
    if value.startswith('\\\\?\\'):
        return path
    return Path('\\\\?\\UNC\\' + value[2:] if value.startswith('\\\\') else '\\\\?\\' + value)


def file_manifest(directory: Path) -> dict[str, str]:
    directory = _filesystem_path(directory)
    return {p.relative_to(directory).as_posix(): sha256(p) for p in sorted(directory.rglob('*')) if p.is_file()}


def tool_manifest(home: Path) -> dict[str, str]:
    for relative in REQUIRED_TOOL_FILES:
        if not _filesystem_path(home/relative).is_file():
            raise ValueError(f'required_tool_file_missing:{relative}')
    manifest = {relative:sha256(_filesystem_path(home/relative)) for relative in REQUIRED_TOOL_FILES[:2]}
    for relative in TOOL_TREES:
        files = file_manifest(home/relative)
        if not files:
            raise ValueError(f'required_tool_tree_missing:{relative}')
        manifest.update({f'{relative}/{name}':digest for name,digest in files.items()})
    return manifest


def verify_tools(home: Path, manifest: dict) -> bool:
    try:
        return isinstance(manifest, dict) and bool(manifest) and manifest == tool_manifest(home)
    except (OSError, ValueError, TypeError):
        return False


def verify_manifest(directory: Path, manifest: dict, *, exact: bool = False) -> bool:
    if not isinstance(manifest, dict) or not manifest:
        return False
    directory = _filesystem_path(directory)
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
        if not config_matches(home):
            return None
        environment = managed.context('esp32s3', home=home)
        if environment is None:
            return None
        prepared_name = receipt.get('prepared_directory', '')
        if not isinstance(prepared_name, str) or not prepared_name.startswith('prepared-') or Path(prepared_name).name != prepared_name:
            return None
        prepared = revision_root/prepared_name
        # The shared context above already verifies every installed component,
        # including offline indexes. Do not hash the same 1.7 GB tree twice.
        if not verify_manifest(prepared/'libraries', receipt.get('files'), exact=True):
            return None
        if not verify_manifest(prepared/'recovery', receipt.get('recovery_files'), exact=True):
            return None
        return {**environment,'libraries':str(prepared/'libraries'),
                'factory_recovery':receipt.get('recovery', []),
                'revision':revision,'backend':'chatmaker-managed-waveshare-s3'}
    except (OSError, ValueError, TypeError):
        return None


def prepare_environment(revision: str, *, dry_run=False) -> dict:
    if revision not in VENDORS:
        return {'success':False,'state':'revision-needed','error':'revision_required'}
    problem = managed.host_problem(dry_run=dry_run)
    if problem:
        return problem
    if dry_run:
        plan = managed.preview('esp32s3', home=root())
        vendor = VENDORS[revision]
        cache = managed.archive_path(vendor)
        cached = cache.is_file() and cache.stat().st_size == vendor['size'] and sha256(cache) == vendor['sha256']
        plan['components'].append({'id':'waveshare-'+revision,'version':revision,'archive_bytes':vendor['size'],
                                   'cached':cached,'sources':vendor['sources']})
        plan['archive_bytes'] += vendor['size']
        if not cached:
            plan['remaining_download_bytes'] += vendor['size']
        return plan
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
            full_receipt = isinstance(previous, dict) and previous.get('preparation_version') == PREPARATION_VERSION
            verifier = verify_tools if full_receipt else verify_manifest
            previous_tools = previous.get('tools', {}) if isinstance(previous, dict) else {}
            if full_receipt and isinstance(previous_tools, dict) and config_matches(home):
                # A revision may have rebased the shared, fully known config.
                # Only that exact local config may refresh this one digest.
                previous_tools = {**previous_tools,'arduino-cli.yaml':sha256(home/'arduino-cli.yaml')}
            if not full_receipt and isinstance(previous_tools, dict):
                # Schema migration rewrites these two files from pinned input;
                # another revision may already have migrated the shared config.
                previous_tools = {name:digest for name,digest in previous_tools.items()
                                  if name not in {'bin/arduino-cli.exe', 'arduino-cli.yaml'}}
            if previous_tools and not verifier(home, previous_tools):
                return {'success':False,'error':'toolchain_cache_changed',
                        'teacher_message':'已准备的编译工具发生变化或缺失，已停止。请保留此缓存供检查，在新的 CHATMAKER_RUNTIME_ROOT 重新准备；不需要安装 Mind+。'}
        preparation = managed.prepare('esp32s3', home=home)
        if not preparation.get('success'):
            return preparation
        vendor_zip = managed.archive_path(VENDORS[revision])
        previous_vendor = managed.runtime_root()/'toolchains/waveshare'/VENDORS[revision]['filename']
        if (not vendor_zip.exists() and previous_vendor.is_file()
                and previous_vendor.stat().st_size == VENDORS[revision]['size']
                and sha256(previous_vendor) == VENDORS[revision]['sha256']):
            from chatmaker.installers.locks import exclusive_file
            import shutil
            with exclusive_file(vendor_zip.with_name(vendor_zip.name+'.lock')):
                shutil.copyfile(previous_vendor, vendor_zip)
        download_locked(VENDORS[revision],vendor_zip,timeout=180)
        emit('stage', stage='vendor', message='准备微雪显示、触摸和恢复固件')
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
        # Core/compiler/SDK integrity is owned by the shared component receipts.
        receipt = {'preparation_version':PREPARATION_VERSION, 'prepared_directory':prepared.name,
                   'core_version':CORE_VERSION,'vendor_sha256':VENDORS[revision]['sha256'],
                   'files':file_manifest(libraries),'managed_profile':'esp32s3',
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
