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
    def make_environment(self, home, *, cli_version=None, omit=()):
        data, ids = chain.selected('esp32')
        if cli_version == '1.3.1':
            data['artifacts']['cli'] = chain.load_runtime_sources()['arduino_cli_fallback'][data['platform_tag']]
        for name in ids:
            if name in omit:
                continue
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
        return data

    def test_installed_index_uses_the_selected_cli_format(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp).resolve()
            data, ids = chain.selected('avr')
            core_index = data['artifacts']['core']['destination'] + '/installed.json'
            latest = chain.generated_files(home, data, ids)
            self.assertEqual(latest[core_index]['version'], 2)
            self.assertNotIn('version', latest['data/package_index.json'])
            data['artifacts']['cli'] = data['fallback_cli']
            compatible = chain.generated_files(home, data, ids)
            self.assertNotIn('version', compatible[core_index])
            self.assertEqual(latest[core_index]['packages'], compatible[core_index]['packages'])

    def test_verified_previous_cli_is_reused_without_network_or_installation(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp).resolve()
            self.make_environment(home, cli_version='1.3.1')
            with mock.patch.object(chain, 'host_problem', return_value=None), \
                 mock.patch.object(chain, 'download_locked') as download:
                result = chain.prepare('esp32', home=home)
            self.assertTrue(result['success'], result)
            self.assertEqual(result['environment']['cli_version'], '1.3.1')
            self.assertFalse(result['installation_performed'])
            download.assert_not_called()

    def test_cached_previous_cli_is_used_when_only_the_cli_is_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp, 'profile').resolve()
            self.make_environment(home, omit=('cli',))
            backup = chain.load_runtime_sources()['arduino_cli_fallback'][chain.platform_tag()]
            with mock.patch.dict(os.environ, {'CHATMAKER_RUNTIME_ROOT': temp}), \
                 mock.patch.object(chain, 'host_problem', return_value=None), \
                 mock.patch.object(chain, 'archive_matches', side_effect=lambda path, item: item == backup), \
                 mock.patch.object(chain, '_seed_previous_cache'), \
                 mock.patch.object(chain, 'download_locked') as download, \
                 mock.patch.object(chain, '_install') as install:
                chain.prepare('esp32', home=home)
            self.assertEqual(install.call_args.args[2], backup)
            self.assertEqual(download.call_args.args[0], backup)

    def test_missing_new_esp32_sdk_falls_back_with_matching_core(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.dict(os.environ, {'CHATMAKER_RUNTIME_ROOT': temp}):
            def download(item, archive, **kwargs):
                if item['filename'] == 'esp32-libs-3.3.12.zip':
                    raise chain.DownloadError('all_pinned_sources_failed')

            def install(home, name, item, archive):
                target = home / item['destination']
                target.mkdir(parents=True, exist_ok=True)
                (target / 'fixture.dat').write_bytes(name.encode('ascii'))
                receipt = home / 'manifests' / (name + '.json')
                receipt.parent.mkdir(exist_ok=True)
                chain._write_json(receipt, {'sha256': item['sha256'], 'destination': item['destination'],
                                            'files': chain.file_manifest(target)})

            with mock.patch.object(chain, 'host_problem', return_value=None), \
                 mock.patch.object(chain, 'download_locked', side_effect=download) as downloads, \
                 mock.patch.object(chain, '_install', side_effect=install):
                result = chain.prepare('esp32')
            self.assertTrue(result['success'], result)
            names = [call.args[0]['filename'] for call in downloads.call_args_list]
            self.assertIn('esp32-libs-3.3.12.zip', names)
            self.assertIn('esp32-libs-3.3.11.zip', names)
            self.assertEqual(result['environment']['core_version'], '3.3.11')
            self.assertEqual(chain.context('esp32'), result['environment'])

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
