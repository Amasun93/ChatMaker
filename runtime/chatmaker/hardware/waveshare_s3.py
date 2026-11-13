"""Exact Waveshare ESP32-S3-Touch-LCD-2.8 V1/V2 compile/upload adapter."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import tempfile
import time

from . import waveshare_toolchain as chain
from .arduino_toolchain import riscv_cpp_include, run_cli as run
from .classroom_cli import dry_run_guard
from .esp32_devkit_v1 import port_matches
from chatmaker.installers.downloads import sha256
from chatmaker.progress import emit

BOARD_ID = 'waveshare-esp32-s3-touch-lcd-2-8'
FQBN = 'esp32:esp32:esp32s3:FlashSize=16M,PartitionScheme=app3M_fat9M_16MB,PSRAM=opi,USBMode=hwcdc,CDCOnBoot=cdc,FlashMode=qio'


def scan_ports() -> list[dict]:
    from serial.tools.list_ports import comports
    return [{'address':p.device,'vid':p.vid,'pid':p.pid,'serial_number':p.serial_number,
             'location':p.location,'description':p.description} for p in comports()]


def select_port(ports: list[dict], requested: str | None) -> dict | None:
    eligible = [p for p in ports if p.get('vid') == 0x303A]
    if requested:
        eligible = [p for p in eligible if port_matches(p['address'], requested)]
    return eligible[0] if len(eligible)==1 else None


def match_application_port(original: dict, ports: list[dict]) -> str | None:
    def same_device(port: dict) -> bool:
        if original.get('serial_number') and port.get('serial_number'):
            return port['serial_number'] == original['serial_number']
        return bool(original.get('location') and port.get('location') == original['location'])

    matches = [p for p in ports if p.get('vid') == 0x303A and same_device(p)]
    return matches[0]['address'] if len(matches)==1 else None


def compile_project(request: dict, context: dict, *, fqbn: str = FQBN, output_suffix: str = 'bin') -> dict:
    build_root = Path(context['root'])/'builds'; build_root.mkdir(parents=True,exist_ok=True)
    build = Path(tempfile.mkdtemp(prefix='project-',dir=build_root))
    if request.get('sketch'):
        sketch = Path(request['sketch']).expanduser().resolve()
        if sketch.is_file():
            sketch = sketch.parent
        if not sketch.is_dir() or not (sketch/(sketch.name+'.ino')).is_file():
            return {'success':False,'error':'sketch_directory_with_matching_ino_required'}
    elif request.get('code'):
        name = re.sub(r'[^a-zA-Z0-9_]', '_', str(request.get('project_name','classroom_project')))
        name = name[:64] or 'classroom_project'
        sketch = build/'source'/name; sketch.mkdir(parents=True)
        (sketch/(name+'.ino')).write_text(str(request['code']),encoding='utf-8')
    else:
        return {'success':False,'error':'sketch_or_code_required'}
    output = build/'compiled'
    emit('stage', stage='compile', message='正在编译程序')
    command = [context['cli'],'--config-file',context['config'],'compile','--fqbn',fqbn,
               '--libraries',context['libraries'],'--build-path',str(output),str(sketch)]
    include = riscv_cpp_include(context)
    options = {'cpp_include': include} if include is not None else {}
    execution = run(command, timeout=int(request.get('timeout', 900)), **options)
    binaries = sorted(output.glob(f'*.{output_suffix}')) if execution.get('returncode')==0 else []
    success = bool(binaries) and (output/f'{sketch.name}.ino.{output_suffix}').is_file()
    return {'success':success,'execution':execution,'fqbn':fqbn,'revision':request.get('revision'),
            'build_path':str(output),'sketch':str(sketch),'artifacts':[{'path':str(p),'size':p.stat().st_size,'sha256':sha256(p)} for p in binaries]}


def execute_request(request: dict) -> dict:
    revision = request.get('revision')
    base = {'board':BOARD_ID,'revision':revision,'action':request.get('action'),'success':False}
    rejected = dry_run_guard(request)
    if rejected:
        return {**base, **rejected}
    if revision not in chain.VENDORS:
        return {**base,'state':'revision-needed','error':'revision_required',
                'teacher_message':'请确认板背面的 V1/V2 标签，再选择对应触摸驱动；暂时不清楚时可继续其他软件准备。'}
    action = request.get('action')
    if action=='prepare-environment':
        return {**base,**chain.prepare_environment(revision, dry_run=request.get('dry_run') is True)}
    if action=='ports':
        return {**base,'success':True,'ports':scan_ports()}
    ctx = chain.context(revision)
    if action=='doctor':
        return {**base,'success':True,'ready_for_compile':ctx is not None,'environment':ctx,
                'required_fqbn':FQBN,'touch_controller':'CST328' if revision=='v1' else 'CST3530'}
    if action not in {'compile','compile-upload'}:
        return {**base,'error':'unsupported_action'}
    if not ctx:
        return {**base,'error':'managed_toolchain_missing','next_action':'prepare-environment'}
    compiled = compile_project(request,ctx)
    result = {**base,'compile':compiled,'stage':'compile','success':compiled.get('success',False)}
    if not compiled.get('success') or action=='compile':
        return result
    if request.get('board_confirmed') is not True:
        return {**result,'success':False,'stage':'identity','error':'board_identity_required',
                'teacher_message':'首次使用请确认连接的确实是这块微雪板及其版本；确认后同一项目可以继续下载。'}
    ports = scan_ports(); selected = select_port(ports,request.get('port'))
    if selected is None:
        return {**result,'success':False,'stage':'awaiting-hardware','ports':ports,
                'teacher_message':'请接入这块板的数据 USB 接口；有多块候选设备时选择本次使用的一块。'}
    # A successfully compiled fresh build is the sole upload source.
    emit('stage', stage='upload', message='正在下载程序到已确认的微雪板')
    command = [ctx['cli'],'--config-file',ctx['config'],'upload','--fqbn',FQBN,
               '--port',selected['address'],'--input-dir',compiled['build_path'],compiled['sketch']]
    execution = run(command,timeout=int(request.get('upload_timeout',180)))
    uploaded = {'success':execution.get('returncode')==0,'port':selected['address'],
                'execution':execution,'application_port':None}
    if uploaded['success']:
        deadline = time.monotonic()+8
        while time.monotonic()<deadline:
            application = match_application_port(selected,scan_ports())
            if application:
                uploaded['application_port'] = application
                break
            time.sleep(0.25)
    return {**result,'success':uploaded['success'],'stage':'complete' if uploaded['success'] else 'upload','upload':uploaded,
            'physical_effect_verified':False,
            'teacher_message':'程序已下载，等待运行信息和实物观察。' if uploaded['success'] else '下载失败，请查看端口占用或下载模式提示；必要时按住 BOOT 并短按 RESET 后重试。'}


def main(argv: list[str] | None = None) -> int:
    from .classroom_cli import main_entry
    return main_entry(execute_request, argv, board_id=BOARD_ID)


if __name__=='__main__':
    raise SystemExit(main())
