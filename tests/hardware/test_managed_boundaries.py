import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from chatmaker.hardware import arduino_toolchain as chain
from chatmaker.hardware import classroom_cli, managed_esp32, waveshare_s3, workflow


class DryRunBoundaryTests(unittest.TestCase):
    def test_common_cli_refuses_mutating_dry_run_before_dispatch(self):
        for action in ('run', 'compile', 'compile-upload'):
            with self.subTest(action=action), contextlib.redirect_stdout(io.StringIO()) as output:
                handler = mock.Mock(return_value={'success': True})
                code = classroom_cli.main_entry(handler, ['--action', action, '--dry-run'])
                self.assertEqual(code, 1)
                self.assertEqual(json.loads(output.getvalue())['error'], 'dry_run_unsupported_action')
                handler.assert_not_called()

    def test_workflow_dry_run_stops_before_environment_or_upload(self):
        adapter = mock.Mock()
        adapter.execute_request.side_effect = [
            {'success': True, 'ready_for_compile': False},
            {'success': True},
            {'success': True, 'compile': {'success': True}, 'upload': {'success': True}},
        ]
        result = workflow.run_project({'action': 'run', 'board_id': 'test-board',
            'code': 'void setup(){} void loop(){}', 'dry_run': True}, adapters={'test-board': adapter})
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'dry_run_unsupported_action')
        adapter.execute_request.assert_not_called()

    def test_direct_adapters_dry_run_never_compiles_or_uploads(self):
        for module, board_id in ((managed_esp32, 'nova-esp32'), (waveshare_s3, waveshare_s3.BOARD_ID)):
            for action in ('compile', 'compile-upload'):
                with self.subTest(board=board_id, action=action), \
                     mock.patch.object(module.chain, 'context', return_value={'cli': 'cli', 'config': 'config'}), \
                     mock.patch.object(module, 'compile_project', return_value={
                         'success': True, 'build_path': 'build', 'sketch': 'project'}) as compile_mock, \
                     mock.patch.object(module, 'scan_ports', return_value=[{
                         'address': 'COM9', 'usb_uart_likely': True, 'vid': 0x303A}]), \
                     mock.patch.object(module, 'run', return_value={'returncode': 1}) as upload_mock:
                    result = module.execute_request({'action': action, 'board_id': board_id,
                        'revision': 'v1', 'code': 'example', 'board_confirmed': True, 'dry_run': True})
                    self.assertFalse(result['success'])
                    self.assertEqual(result['error'], 'dry_run_unsupported_action')
                    compile_mock.assert_not_called()
                    upload_mock.assert_not_called()


class ManagedProcessEnvironmentTests(unittest.TestCase):
    def test_child_cannot_inherit_arduino_config_overrides(self):
        overrides = {'ARDUINO_DIRECTORIES_DATA': 'foreign-data',
                     'arduino_board_manager_additional_urls': 'https://outside.example/index.json',
                     'CHATMAKER_TEST_KEEP': 'keep'}
        with mock.patch.dict(os.environ, overrides):
            result = chain.run_cli([sys.executable, '-c',
                "import json,os; print(json.dumps({k:v for k,v in os.environ.items() if k.upper().startswith('ARDUINO_') or k=='CHATMAKER_TEST_KEEP'}))"])
            self.assertEqual(result['returncode'], 0, result)
            self.assertEqual(json.loads(result['stdout']), {'CHATMAKER_TEST_KEEP': 'keep'})
            self.assertEqual(os.environ['ARDUINO_DIRECTORIES_DATA'], 'foreign-data')


class ManagedSearchRootTests(unittest.TestCase):
    def make_environment(self, home):
        data, ids = chain.selected('esp32')
        for name in ids:
            item = data['artifacts'][name]
            target = home / item['destination']
            target.mkdir(parents=True, exist_ok=True)
            (target / 'fixture.dat').write_bytes(name.encode('ascii'))
            receipt = home / 'manifests' / (name + '.json')
            receipt.parent.mkdir(exist_ok=True)
            chain._write_json(receipt, {'sha256': item['sha256'], 'destination': item['destination'],
                                        'files': chain.file_manifest(target)})
        for name, value in chain.generated_files(home, data, ids).items():
            target = home / name
            target.parent.mkdir(parents=True, exist_ok=True)
            chain._write_json(target, value)
        chain._write_json(home / 'receipt.json', {'schema': 1, 'profile': 'esp32', 'artifacts': ids, 'libraries': []})

    def test_unregistered_search_inputs_invalidate_ready_without_deleting_files(self):
        additions = (
            'libraries/UnreceiptedLibrary/UnreceiptedLibrary.h',
            'user/libraries/UnreceiptedLibrary/UnreceiptedLibrary.h',
            'user/hardware/thirdparty/esp32/platform.txt',
            'data/packages/esp32/hardware/esp32/99.0.0/platform.txt',
            'data/packages/esp32/tools/esp-x32/unknown/tool.exe',
        )
        for relative in additions:
            with self.subTest(path=relative), tempfile.TemporaryDirectory() as temp:
                home = Path(temp).resolve()
                self.make_environment(home)
                self.assertIsNotNone(chain.context('esp32', home=home))
                added = home / relative
                added.parent.mkdir(parents=True, exist_ok=True)
                added.write_text('unregistered input')
                self.assertIsNone(chain.context('esp32', home=home))
                self.assertEqual(added.read_text(), 'unregistered input')
