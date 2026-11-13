import io
import os
from pathlib import Path
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from chatmaker.hardware import arduino_toolchain, esp32_devkit_v1, managed_avr, workflow


class MacArduinoPreparationTests(unittest.TestCase):
    def test_preview_selects_mac_architecture_and_only_the_requested_chip(self):
        for architecture, archive_arch in [('arm64', 'aarch64'), ('x86_64', 'x86_64')]:
            with self.subTest(architecture=architecture), tempfile.TemporaryDirectory() as temp, \
                 mock.patch.object(arduino_toolchain.platform, 'system', return_value='Darwin'), \
                 mock.patch.object(arduino_toolchain.platform, 'machine', return_value=architecture), \
                 mock.patch.dict(os.environ, {'CHATMAKER_RUNTIME_ROOT': str(Path(temp) / 'runtime')}):
                result = workflow.run_project({'action': 'prepare-environment', 'dry_run': True,
                    'board_id': 'waveshare-esp32-s3-touch-lcd-2-8', 'revision': 'v2'})
                self.assertTrue(result['success'], result)
                by_id = {entry['id']: entry for entry in result['components']}
                self.assertIn(f'{archive_arch}-apple-darwin.tar.gz', by_id['esp-x32']['sources'][0]['url'])
                self.assertIn('esp32s3-libs', by_id)
                self.assertNotIn('esp32-libs', by_id)
                self.assertNotIn('esp-rv32', by_id)
                self.assertFalse(Path(temp, 'runtime').exists())

    def test_avr_and_riscv_use_separate_compilers_and_matching_platforms(self):
        with mock.patch.object(arduino_toolchain.platform, 'system', return_value='Darwin'), \
             mock.patch.object(arduino_toolchain.platform, 'machine', return_value='arm64'):
            avr, avr_ids = arduino_toolchain.selected('avr')
            self.assertIn('avr-gcc', avr_ids)
            self.assertNotIn('esp-x32', avr_ids)
            self.assertEqual(arduino_toolchain.offline_index(avr, avr_ids)['packages'][0]['name'], 'arduino')
            riscv, riscv_ids = arduino_toolchain.selected('esp32c3')
            self.assertIn('esp-rv32', riscv_ids)
            self.assertIn('esp32c3-libs', riscv_ids)
            self.assertNotIn('esp-x32', riscv_ids)
            self.assertEqual(riscv['artifacts']['esp-rv32']['system']['host'], 'arm64-apple-darwin')

    def test_missing_rosetta_stops_before_download_or_install(self):
        with tempfile.TemporaryDirectory() as temp, \
             mock.patch.dict(os.environ, {'CHATMAKER_RUNTIME_ROOT': str(Path(temp) / 'runtime')}), \
             mock.patch.object(arduino_toolchain.platform, 'system', return_value='Darwin'), \
             mock.patch.object(arduino_toolchain.platform, 'machine', return_value='arm64'), \
             mock.patch.object(arduino_toolchain, 'rosetta_available', return_value=False, create=True), \
             mock.patch.object(arduino_toolchain, 'download_locked') as download:
            result = arduino_toolchain.prepare('esp32s3')
            self.assertEqual(result['error'], 'rosetta_required')
            self.assertFalse(Path(temp, 'runtime').exists())
            download.assert_not_called()


class MacArchiveTests(unittest.TestCase):
    def make_archive(self, path, *, unsafe=False):
        with tarfile.open(path, 'w:gz') as tar:
            binary = tarfile.TarInfo('tool/bin/compiler')
            binary.mode = 0o755
            binary.size = 4
            tar.addfile(binary, io.BytesIO(b'tool'))
            hardlink = tarfile.TarInfo('tool/bin/alias')
            hardlink.type = tarfile.LNKTYPE
            hardlink.linkname = 'tool/bin/compiler'
            tar.addfile(hardlink)
            symlink = tarfile.TarInfo('tool/lib/plugin')
            symlink.type = tarfile.SYMTYPE
            symlink.linkname = '../../outside' if unsafe else '../bin/compiler'
            tar.addfile(symlink)

    def test_archive_preserves_executable_file_aliases(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            archive = directory / 'tool.tar.gz'
            self.make_archive(archive)
            out = directory / 'out'
            arduino_toolchain.extract_archive(archive, out, strip_root=True)
            for relative in ('bin/compiler', 'bin/alias', 'lib/plugin'):
                self.assertEqual((out / relative).read_bytes(), b'tool')
                if os.name != 'nt':
                    self.assertTrue(os.access(out / relative, os.X_OK))

    def test_archive_rejects_a_link_outside_the_stripped_root(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            archive = directory / 'tool.tar.gz'
            self.make_archive(archive, unsafe=True)
            with self.assertRaises(ValueError):
                arduino_toolchain.extract_archive(archive, directory / 'out', strip_root=True)
            self.assertFalse((directory / 'out').exists())


class MacSerialPortTests(unittest.TestCase):
    def test_callout_port_preserves_device_case_and_recognizes_usb_bridge(self):
        device = SimpleNamespace(device='/dev/cu.SLAB_USBtoUART', description='UART Bridge',
            hwid='USB VID:PID=10C4:EA60', manufacturer=None, vid=0x10C4, pid=0xEA60)
        with mock.patch('serial.tools.list_ports.comports', return_value=[device]):
            port, = esp32_devkit_v1.scan_ports()
        self.assertEqual(port['address'], device.device)
        self.assertTrue(port['usb_uart_likely'])

    def test_nano_bootloader_choice_and_mac_port_reach_real_entry(self):
        port = '/dev/cu.usbserial-Ab12'
        request = {'board_id': 'arduino-nano-classic', 'code': 'void setup() {} void loop() {}',
                   'board_confirmed': True, 'port': port}
        with mock.patch.object(managed_avr.chain, 'context', return_value={'cli': 'cli', 'config': 'config'}), \
             mock.patch.object(managed_avr, 'compile_project', return_value={
                 'success': True, 'build_path': 'build', 'sketch': 'sketch'}), \
             mock.patch.object(managed_avr, 'scan_ports', return_value=[{
                 'address': port, 'usb_uart_likely': True, 'is_bluetooth': False}]), \
             mock.patch.object(managed_avr.chain, 'run_cli', return_value={'returncode': 0}) as run:
            result = workflow.run_project({**request, 'action': 'compile-upload', 'bootloader': 'old'})
            self.assertTrue(result['success'], result)
            command = run.call_args.args[0]
            self.assertEqual(command[command.index('--fqbn') + 1], 'arduino:avr:nano:cpu=atmega328old')
            self.assertEqual(command[command.index('--port') + 1], port)

    def test_nano_automatic_bootloader_retry_is_limited_to_sync_failure(self):
        port = '/dev/cu.usbserial-Ab12'
        request = {'board_id': 'arduino-nano-classic', 'action': 'compile-upload', 'code': 'example',
                   'board_confirmed': True, 'port': port}
        for stderr, count in [('avrdude: not in sync', 2), ('avrdude: invalid device signature', 1)]:
            with self.subTest(stderr=stderr), \
                 mock.patch.object(managed_avr.chain, 'context', return_value={'cli': 'cli', 'config': 'config'}), \
                 mock.patch.object(managed_avr, 'compile_project', return_value={
                     'success': True, 'build_path': 'build', 'sketch': 'sketch'}), \
                 mock.patch.object(managed_avr, 'scan_ports', return_value=[{
                     'address': port, 'usb_uart_likely': True, 'is_bluetooth': False}]), \
                 mock.patch.object(managed_avr.chain, 'run_cli', side_effect=[
                     {'returncode': 1, 'stderr': stderr}, {'returncode': 0}]) as run:
                result = workflow.run_project(request)
                self.assertEqual(run.call_count, count)
                self.assertEqual(result['success'], count == 2)
                if count == 2:
                    self.assertIn('arduino:avr:nano:cpu=atmega328old', run.call_args.args[0])
