import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

from chatmaker.hardware import arduino_toolchain, managed_avr, managed_esp32, workflow


class PreparationPreviewTests(unittest.TestCase):
    def test_classic_preview_is_read_only_and_selects_one_chip(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {'CHATMAKER_RUNTIME_ROOT': tmp + '/runtime'}):
            result = workflow.run_project({'action': 'prepare-environment', 'board_id': 'esp32-devkit-v1', 'dry_run': True})
            self.assertTrue(result['success'], result)
            self.assertFalse(Path(tmp, 'runtime').exists())
        names = [c['id'] for c in result['components']]
        versions = {c['id']: c['version'] for c in result['components']}
        self.assertIn('esp32-libs', names)
        self.assertEqual(versions['core'], '3.3.12')
        self.assertEqual(versions['esp32-libs'], versions['core'])
        self.assertNotIn('esp32s3-libs', names)
        self.assertNotIn('esp-rv32', names)
        self.assertLess(result['archive_bytes'], 800_000_000)

    def test_new_vendor_profiles_use_the_exact_core_and_host_tools(self):
        for host in ('windows-amd64', 'macos-arm64', 'macos-x86_64'):
            for profile, vendor, tool in (
                ('renesas_uno', 'arduino', 'bossac'),
                ('unihiker_k10', 'UNIHIKER', 'esptool_py'),
            ):
                with self.subTest(host=host, profile=profile), \
                     mock.patch.object(arduino_toolchain, 'platform_tag', return_value=host):
                    bundle, ids = arduino_toolchain.selected(profile)
                    package = arduino_toolchain.offline_index(bundle, ids)['packages'][0]
                    self.assertEqual(package['name'], vendor)
                    self.assertIn(tool, [entry['name'] for entry in package['tools']])
                    self.assertNotIn('esp-x32', ids)
                    if host.startswith('macos'):
                        self.assertIn('-apple-darwin', bundle['artifacts'][tool]['system']['host'])


class ManagedArchiveTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.find_spec('chatmaker.hardware.arduino_toolchain')
        self.assertIsNotNone(spec, 'shared isolated Arduino preparation is missing')
        from chatmaker.hardware import arduino_toolchain
        self.chain = arduino_toolchain

    def test_component_install_retries_transient_windows_rename_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            archive = root / 'component.zip'
            with zipfile.ZipFile(archive, 'w') as bundle:
                bundle.writestr('tool.exe', b'fixture')
            item = {'destination': 'tools/fixture', 'strip_root': False, 'sha256': self.chain.sha256(archive)}
            original_rename = Path.rename
            attempts = []

            def rename(source, destination):
                attempts.append(source)
                if len(attempts) == 1:
                    raise PermissionError('transient access denied')
                return original_rename(source, destination)

            with mock.patch.object(Path, 'rename', rename):
                self.chain._install(root, 'tool', item, archive)
            self.assertEqual(len(attempts), 2)
            self.assertTrue(self.chain._artifact_ready(root, 'tool', item))

    def test_zip_cannot_write_outside_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / 'tool.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('tool/../../escaped', 'bad')
            with self.assertRaises(ValueError):
                self.chain.extract_archive(archive, root / 'out', strip_root=True)
            self.assertFalse((root / 'escaped').exists())

    def test_core_receipt_excludes_replaced_vendor_installed_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp).resolve()
            archive = folder / 'core.zip'
            with zipfile.ZipFile(archive, 'w') as source:
                source.writestr('boards.txt', 'test board')
                source.writestr('installed.json', '{}')
            item = {'destination': 'core', 'strip_root': False, 'sha256': self.chain.sha256(archive)}
            self.chain._install(folder, 'core', item, archive)
            (folder / 'core/installed.json').write_text('{"managed":true}', encoding='utf-8')
            self.assertTrue(self.chain._artifact_ready(folder, 'core', item))

    def test_full_tree_manifest_detects_removed_sdk_header_and_extra_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sdk.h').write_text('sdk')
            (root / 'compiler.exe').write_bytes(b'compiler')
            manifest = self.chain.file_manifest(root)
            (root / 'sdk.h').unlink()
            self.assertFalse(self.chain.verify_manifest(root, manifest))
            (root / 'sdk.h').write_text('sdk')
            (root / 'injected.cpp').write_text('extra')
            self.assertFalse(self.chain.verify_manifest(root, manifest))


class ManagedUploadTests(unittest.TestCase):
    def test_classic_upload_requires_explicit_board_confirmation(self):
        spec = importlib.util.find_spec('chatmaker.hardware.managed_esp32')
        self.assertIsNotNone(spec, 'managed classic ESP32 adapter is missing')
        from chatmaker.hardware import managed_esp32
        with mock.patch.object(managed_esp32.chain, 'context', return_value={'root': 'test'}), \
             mock.patch.object(managed_esp32, 'compile_project', return_value={'success': True}), \
             mock.patch.object(managed_esp32, 'run') as run:
            result = managed_esp32.execute_request({'action': 'compile-upload', 'code': 'x'})
        self.assertEqual(result['error'], 'board_identity_required')
        run.assert_not_called()

    def test_uno_r4_rejects_an_unrelated_usb_serial_port(self):
        request = {'action': 'compile-upload', 'board_id': 'arduino-uno-r4-wifi',
                   'code': 'x', 'board_confirmed': True, 'port': 'COM5'}
        context = {'cli': 'cli', 'config': 'config'}
        compiled = {'success': True, 'build_path': 'build', 'sketch': 'sketch'}
        generic = {'address': 'COM5', 'vid': 0x303A, 'pid': 0x1001,
                   'is_bluetooth': False, 'usb_uart_likely': True}
        with mock.patch.object(managed_avr.chain, 'context', return_value=context) as ready, \
             mock.patch.object(managed_avr, 'compile_project', return_value=compiled) as compile_, \
             mock.patch.object(managed_avr, 'scan_ports', return_value=[generic]), \
             mock.patch.object(managed_avr.chain, 'run_cli') as run:
            result = workflow.run_project(request)
        self.assertEqual(result['stage'], 'awaiting-hardware')
        self.assertEqual(ready.call_args.args, ('renesas_uno',))
        self.assertEqual(compile_.call_args.kwargs['output_suffix'], 'bin')
        run.assert_not_called()

    def test_native_board_requires_explicit_selection_for_generic_usb(self):
        context = {'cli': 'cli', 'config': 'config'}
        compiled = {'success': True, 'build_path': 'build', 'sketch': 'sketch'}
        generic = {'address': 'COM5', 'vid': 0x303A, 'pid': 0x1001, 'serial_number': 'device'}
        for board in ('unihiker-k10', 'seeed-xiao-esp32s3', 'seeed-xiao-esp32s3-sense'):
            with self.subTest(board=board), \
                 mock.patch.object(managed_esp32.chain, 'context', return_value=context), \
                 mock.patch.object(managed_esp32, 'compile_project', return_value=compiled), \
                 mock.patch.object(managed_esp32, 'scan_ports', return_value=[generic]), \
                 mock.patch.object(managed_esp32, 'run', return_value={'returncode': 0}) as run:
                request = {'action': 'compile-upload', 'board_id': board, 'code': 'x', 'board_confirmed': True}
                preview = workflow.run_project(request)
                self.assertEqual(preview['stage'], 'awaiting-hardware')
                run.assert_not_called()
                upload = workflow.run_project({**request, 'port': 'COM5'})
                self.assertTrue(upload['success'], upload)
                command = run.call_args.args[0]
                self.assertEqual(command[command.index('--port') + 1], 'COM5')
                self.assertEqual(upload['upload']['application_port'], 'COM5')
