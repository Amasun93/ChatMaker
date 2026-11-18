import tempfile
import json
import os
import unittest
from pathlib import Path
from unittest import mock
import zipfile

from chatmaker.hardware import waveshare_s3 as board
from chatmaker.hardware import waveshare_toolchain as chain


class WaveshareTests(unittest.TestCase):
    def test_compile_uses_canonical_s3_headers_and_exports_only_this_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            sketch = root / 'demo'
            sketch.mkdir()
            (sketch / 'demo.ino').write_text('void setup(){} void loop(){}')
            build = root / 'cache with spaces'
            ctx = {'cli': 'cli', 'config': 'config', 'libraries': 'libs', 'root': str(root),
                   'platform': 'windows-amd64', 'profile': 'esp32s3'}
            request = {'sketch': str(sketch), 'revision': 'v2', 'build_path': str(build),
                       'compile_timeout': 1800, 'jobs': 2}

            def compiler(command, *, timeout, cpp_include):
                self.assertEqual(timeout, 1800)
                self.assertEqual(command[command.index('--jobs') + 1], '2')
                self.assertEqual(Path(command[command.index('--build-path') + 1]), build)
                include = cpp_include.split(os.pathsep)
                self.assertTrue(include[0].endswith(str(Path('xtensa-esp-elf/include/c++/14.2.0'))))
                self.assertTrue(include[1].endswith(str(Path('xtensa-esp-elf/esp32s3/no-rtti'))))
                self.assertNotIn('--output-dir', command)
                self.assertFalse((build / 'demo.ino.bin').exists())
                if not compiled:
                    (build / 'demo.ino.bin').write_bytes(b'first')
                    (build / 'keep.o').write_bytes(b'cached object')
                return {'returncode': 0}

            compiled = None
            with mock.patch.object(board, 'run', side_effect=compiler):
                compiled = board.compile_project(request, ctx)
                missing = board.compile_project(request, ctx)
            self.assertTrue(compiled['success'])
            self.assertFalse(missing['success'])
            self.assertEqual(missing['error'], 'compile_artifact_missing')
            self.assertEqual(Path(compiled['artifacts'][0]['path']).read_bytes(), b'first')
            self.assertEqual((build / 'keep.o').read_bytes(), b'cached object')

    def test_fixed_build_path_leaves_unrelated_nonempty_directory_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build = root / 'notes'
            build.mkdir()
            note = build / 'keep.txt'
            note.write_text('keep')
            sketch = root / 'demo'
            sketch.mkdir()
            (sketch / 'demo.ino').write_text('void setup(){} void loop(){}')
            ctx = {'cli': 'cli', 'config': 'config', 'libraries': 'libs', 'root': str(root)}
            with mock.patch.object(board, 'run') as run:
                result = board.compile_project({'sketch': str(sketch), 'build_path': str(build)}, ctx)
            self.assertEqual(result['error'], 'build_path_not_owned')
            self.assertEqual(note.read_text(), 'keep')
            run.assert_not_called()

    def make_receipt(self, home, tools):
        if len(tools) > 2:
            data, ids = chain.managed.selected('esp32s3')
            for name in ids:
                item = data['artifacts'][name]
                target = home/item['destination']; target.mkdir(parents=True,exist_ok=True)
                if not any(target.rglob('*')):
                    (target/'fixture').write_bytes(b'tool')
                receipt_path = home/'manifests'/(name+'.json'); receipt_path.parent.mkdir(exist_ok=True)
                receipt_path.write_text(json.dumps({'sha256':item['sha256'],'destination':item['destination'],
                    'files':chain.managed.file_manifest(target,exclude=('installed.json',) if name=='core' else ())}))
            for name,value in chain.managed.generated_files(home,data,ids).items():
                target=home/name; target.parent.mkdir(parents=True,exist_ok=True)
                if name!='arduino-cli.yaml':
                    target.write_text(json.dumps(value))
            (home/'receipt.json').write_text(json.dumps({'schema':1,'profile':'esp32s3','artifacts':ids,'libraries':[]}))
            tools=chain.tool_manifest(home)
        prepared=home/'revisions/v1/prepared-test'
        libraries=prepared/'libraries'; libraries.mkdir(parents=True)
        (libraries/'driver.cpp').write_text('driver')
        recovery=prepared/'recovery'; recovery.mkdir()
        (recovery/'factory.bin').write_bytes(b'factory image')
        receipt={'preparation_version':chain.PREPARATION_VERSION,'prepared_directory':prepared.name,
                 'core_version':chain.CORE_VERSION,'vendor_sha256':chain.VENDORS['v1']['sha256'],
                 'files':chain.file_manifest(libraries),'tools':tools,
                 'recovery_files':chain.file_manifest(recovery)}
        (prepared.parent/'receipt.json').write_text(json.dumps(receipt))

    def test_small_tools_receipt_cannot_certify_an_incomplete_compiler(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp).resolve(); (home/'bin').mkdir(); (home/'bin/arduino-cli.exe').write_bytes(b'cli')
            (home/'arduino-cli.yaml').write_text(json.dumps(chain.configuration(home)))
            self.make_receipt(home,{name:chain.sha256(home/name) for name in ('bin/arduino-cli.exe','arduino-cli.yaml')})
            with mock.patch.object(chain,'root',return_value=home):
                self.assertIsNone(chain.context('v1'))

    def test_compiler_core_and_sdk_files_are_all_in_the_integrity_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp).resolve()
            for relative in chain.REQUIRED_TOOL_FILES:
                path=home/relative; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(b'tool')
            (home/'arduino-cli.yaml').write_text(json.dumps(chain.configuration(home)))
            sdk_extra=home/f'data/packages/esp32/tools/esp32s3-libs/{chain.CORE_VERSION}/include/freertos/extra.h'
            sdk_extra.parent.mkdir(parents=True,exist_ok=True); sdk_extra.write_bytes(b'sdk dependency')
            manifest=chain.tool_manifest(home)
            self.assertIn(sdk_extra.relative_to(home).as_posix(),manifest)
            self.make_receipt(home,manifest)
            targets=[home/'data/packages/esp32/tools/esp-x32/2601/bin/xtensa-esp32s3-elf-gcc.exe',
                     home/f'data/packages/esp32/hardware/esp32/{chain.CORE_VERSION}/cores/esp32/HardwareSerial.cpp',sdk_extra]
            with mock.patch.object(chain,'root',return_value=home):
                self.assertIsNotNone(chain.context('v1'))
                for target in targets:
                    with self.subTest(target=target.name):
                        original=target.read_bytes(); target.unlink()
                        self.assertIsNone(chain.context('v1'))
                        target.write_bytes(original)

    def test_receipt_for_a_config_pointing_elsewhere_is_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp).resolve()
            for relative in chain.REQUIRED_TOOL_FILES:
                path=home/relative; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(b'tool')
            (home/'arduino-cli.yaml').write_text(json.dumps({'directories':{'data':'C:/another-computer/data'}}))
            self.make_receipt(home,chain.tool_manifest(home))
            with mock.patch.object(chain,'root',return_value=home):
                self.assertIsNone(chain.context('v1'))

    def test_domestic_only_with_cached_cli_never_starts_core_network_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp).resolve()
            with zipfile.ZipFile(home/chain.CLI['filename'],'w') as archive:
                archive.writestr('arduino-cli.exe',b'previously verified CLI')
            with mock.patch.object(chain,'root',return_value=home), mock.patch.object(chain.platform,'system',return_value='Windows'), mock.patch.object(chain.platform,'machine',return_value='AMD64'), mock.patch.dict(os.environ,{'CHATMAKER_DOWNLOAD_POLICY':'domestic-only','CHATMAKER_RUNTIME_ROOT':str(home/'runtime')}), mock.patch.object(chain,'download_locked'), mock.patch.object(chain,'run',return_value={'returncode':1}) as run:
                result=chain.prepare_environment('v1')
            self.assertEqual(result['error'],'environment_preparation_failed')
            self.assertIn('domestic_source_not_configured',result['detail'])
            run.assert_not_called()

    def test_domestic_only_reuses_a_complete_environment_without_network(self):
        with mock.patch.object(chain,'context',return_value={'revision':'v1'}), mock.patch.object(chain.platform,'system',return_value='Windows'), mock.patch.object(chain.platform,'machine',return_value='AMD64'), mock.patch.dict(os.environ,{'CHATMAKER_DOWNLOAD_POLICY':'domestic-only'}), mock.patch.object(chain,'run') as run, mock.patch.object(chain,'download_locked') as download:
            result=chain.prepare_environment('v1')
        self.assertTrue(result['success'])
        self.assertFalse(result['installation_performed'])
        run.assert_not_called()
        download.assert_not_called()

    def test_unknown_revision_does_not_prepare_or_scan_hardware(self):
        with mock.patch.object(chain, 'prepare_environment') as prepare, mock.patch.object(board, 'scan_ports') as scan:
            result = board.execute_request({'action': 'compile-upload', 'code': 'x'})
        self.assertEqual(result['state'], 'revision-needed')
        prepare.assert_not_called()
        scan.assert_not_called()

    def test_multiple_or_unrelated_usb_devices_are_not_auto_selected(self):
        ports = [{'address': 'COM2', 'vid': 0x303A}, {'address': 'COM3', 'vid': 0x303A}]
        self.assertIsNone(board.select_port(ports, None))
        self.assertEqual(board.select_port(ports, 'COM3')['address'], 'COM3')
        self.assertIsNone(board.select_port([{'address': 'COM4', 'vid': 0x10C4}], None))

    def test_compile_failure_never_uploads_stale_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            sketch = Path(tmp)/'demo'; sketch.mkdir(); (sketch/'demo.ino').write_text('bad')
            context = {'cli': 'cli.exe', 'config': 'config.yaml', 'libraries': tmp, 'root': tmp}
            with mock.patch.object(chain, 'context', return_value=context), mock.patch.object(board, 'run', return_value={'returncode': 1, 'stdout': '', 'stderr': 'compiler error'}) as run:
                result = board.execute_request({'action': 'compile-upload', 'revision': 'v1', 'sketch': str(sketch), 'board_confirmed': True})
            self.assertEqual(result['stage'], 'compile')
            self.assertFalse(result['success'])
            self.assertEqual(run.call_count, 1)
            self.assertIn('esp32:esp32:esp32s3', run.call_args.args[0][run.call_args.args[0].index('--fqbn')+1])
            self.assertIn('--config-file', run.call_args.args[0])

    def test_upload_requires_boolean_physical_identity_confirmation(self):
        for confirmed in (None, False, 'true'):
            with self.subTest(confirmed=confirmed), mock.patch.object(board, 'compile_project', return_value={'success': True, 'build_path': 'out'}), mock.patch.object(chain, 'context', return_value={'root': 'root'}), mock.patch.object(board, 'run') as run:
                result = board.execute_request({'action': 'compile-upload', 'revision': 'v2', 'code': 'x', 'board_confirmed': confirmed})
                self.assertFalse(result['success'])
                self.assertEqual(result['error'], 'board_identity_required')
                run.assert_not_called()

    def test_v2_driver_selection_updates_real_generated_vendor_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp)/'vendor.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                base = 'Arduino/examples/LVGL_Arduino/'
                z.writestr(base+'Display_ST7789.cpp', 'void LCD_Init(){ Touch_Init(); }')
                z.writestr(base+'LVGL_Driver.cpp', 'Touch_Read_Data(); Touch_Get_XY(); CST328_LCD_TOUCH_MAX_POINTS;')
                for n in ('Display_ST7789.h','LVGL_Driver.h','Touch_CST328.h','Touch_CST3530.h','Touch_CST3530.cpp'):
                    z.writestr(base+n, '// source')
                for name in chain.MOTION_FILES:
                    z.writestr(base+name, '// motion')
                z.writestr(base+'Audio_PCM5101.h', '// depends on the vendor SD and audio stack')
                z.writestr('Arduino/libraries/lvgl/library.properties', 'name=lvgl\nversion=8.3.10')
                z.writestr('Arduino/libraries/lvgl/src/lvgl.h', '// header')
                z.writestr('Arduino/libraries/lvgl/../../escape.txt', 'bad')
            with self.assertRaises(ValueError):
                chain.extract_vendor(archive, Path(tmp)/'bad', 'v2')
            with zipfile.ZipFile(archive, 'a') as z:
                pass
            # Rebuild without the malicious member; exercise the real extractor.
            good = Path(tmp)/'good.zip'
            with zipfile.ZipFile(archive) as src, zipfile.ZipFile(good,'w') as dst:
                for n in src.namelist():
                    if '..' not in n:
                        dst.writestr(n,src.read(n))
            root=Path(tmp)/'libraries'; chain.extract_vendor(good,root,'v2')
            display=(root/'WaveshareBoard/src/Display_ST7789.cpp').read_text()
            touch=(root/'WaveshareBoard/src/LVGL_Driver.cpp').read_text()
            self.assertIn('TOUCH2_Init()', display)
            self.assertIn('Touch2_Read_Data()', touch)
            self.assertIn('Touch2_Get_XY()', touch)
            self.assertNotIn('CST328_LCD_TOUCH_MAX_POINTS',touch)
            self.assertTrue((root/'WaveshareMotion/src/Gyro_QMI8658.cpp').is_file())
            self.assertTrue((root/'WaveshareMotion/src/I2C_Driver.h').is_file())
            self.assertEqual(list(root.rglob('Audio_PCM5101.h')), [])
            chain.extract_vendor(good, Path(tmp)/'v1', 'v1')
            self.assertFalse((Path(tmp)/'v1/WaveshareMotion').exists())

    def test_modified_manifest_file_is_not_accepted_as_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); (p/'driver.cpp').write_text('original')
            manifest=chain.file_manifest(p)
            self.assertTrue(chain.verify_manifest(p,manifest))
            (p/'driver.cpp').write_text('changed')
            self.assertFalse(chain.verify_manifest(p,manifest))
            self.assertFalse(chain.verify_manifest(p,{}))

    def test_extra_driver_cannot_silently_change_a_verified_library(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); (p/'driver.cpp').write_text('original')
            manifest=chain.file_manifest(p)
            (p/'old_revision.cpp').write_text('unintended compiled source')
            self.assertFalse(chain.verify_manifest(p,manifest,exact=True))

    def test_zero_exit_without_fresh_program_binary_does_not_upload(self):
        with tempfile.TemporaryDirectory() as tmp:
            stale=Path(tmp)/'builds/previous/compiled'; stale.mkdir(parents=True)
            (stale/'classroom_project.ino.bin').write_bytes(b'old firmware')
            context={'cli':'cli.exe','config':'config.yaml','libraries':tmp,'root':tmp}
            with mock.patch.object(chain,'context',return_value=context), mock.patch.object(board,'run',return_value={'returncode':0}) as run:
                result=board.execute_request({'action':'compile-upload','revision':'v1','code':'x','board_confirmed':True})
            self.assertFalse(result['success'])
            self.assertEqual(result['stage'],'compile')
            self.assertEqual(run.call_count,1)

    def test_a_changed_serial_at_the_same_usb_socket_is_not_the_same_board(self):
        original={'address':'COM2','serial_number':'unit-a','location':'1-2'}
        replacement=[{'address':'COM8','vid':0x303A,'serial_number':'unit-b','location':'1-2'}]
        self.assertIsNone(board.match_application_port(original,replacement))

    def test_core_damage_is_not_blessed_by_making_a_new_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp).resolve(); revision_root=home/'revisions/v1'; revision_root.mkdir(parents=True)
            core_file=home/'data/boards.txt'; core_file.parent.mkdir(); core_file.write_text('verified')
            receipt={'tools':{'data/boards.txt':chain.sha256(core_file)}}
            (revision_root/'receipt.json').write_text(json.dumps(receipt))
            core_file.write_text('damaged')
            with mock.patch.object(chain,'root',return_value=home), mock.patch.object(chain.platform,'system',return_value='Windows'), mock.patch.object(chain.platform,'machine',return_value='AMD64'), mock.patch.object(chain,'download_locked') as download:
                result=chain.prepare_environment('v1')
            self.assertEqual(result['error'],'toolchain_cache_changed')
            self.assertFalse(result['success'])
            download.assert_not_called()
            self.assertEqual(json.loads((revision_root/'receipt.json').read_text()),receipt)

    def test_usb_reenumeration_does_not_follow_an_unrelated_board(self):
        original={'address':'COM2','serial_number':'unit-a','location':'1-2'}
        ports=[{'address':'COM7','vid':0x303A,'serial_number':'unit-b','location':'1-3'},
               {'address':'COM8','vid':0x303A,'serial_number':'unit-a','location':'1-2'}]
        self.assertEqual(board.match_application_port(original,ports),'COM8')
        self.assertIsNone(board.match_application_port(original,ports[:1]))
