import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from chatmaker.hardware import esp32_devkit_v1 as adapter


class CoreInventoryCompatibilityTests(unittest.TestCase):
    def probe(self, inventory):
        def runner(command, timeout):
            value = inventory if 'list' in command else {
                'fqbn': 'esp32:esp32:esp32doit-devkit-v1', 'name': 'DOIT ESP32 DEVKIT V1'}
            return {'returncode': 0, 'stdout': json.dumps(value), 'stderr': ''}
        return adapter.probe_candidate({'cli': 'cli.exe', 'backend': 'official'}, runner=runner)

    def test_modern_cli_installed_core_is_recognized(self):
        result = self.probe({'platforms': [{'id': 'esp32:esp32',
            'installed_version': '3.3.11', 'latest_version': '3.3.12',
            'releases': {'3.3.11': {'name': 'esp32', 'version': '3.3.11'}}}]})
        self.assertTrue(result['ready_for_compile'])
        self.assertEqual(result['core_version'], '3.3.11')

    def test_available_new_version_is_not_mistaken_for_installed_version(self):
        result = self.probe({'platforms': [{'id': 'esp32:esp32',
            'installed_version': '3.3.10', 'latest_version': '3.3.11'}]})
        self.assertTrue(result['core_inventory_valid'])
        self.assertFalse(result['ready_for_compile'])
        self.assertEqual(result['error'], 'exact_esp32_core_not_found')


    def test_empty_modern_inventory_means_missing_core_not_broken_protocol(self):
        result = self.probe({'platforms': []})
        self.assertTrue(result['core_inventory_valid'])
        self.assertEqual(result['error'], 'exact_esp32_core_not_found')


class ClassroomEntryTests(unittest.TestCase):
    def command(self, *args):
        return subprocess.run([sys.executable, '-m', 'chatmaker.hardware.workflow', *args],
                              capture_output=True, encoding='utf-8', timeout=20)

    def test_version_reports_the_source_actually_loaded(self):
        result = self.command('--version')
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(Path(value['runtime']['source_root']), Path(__file__).resolve().parents[2])
        self.assertRegex(value['runtime']['source_commit'], r'^[0-9a-f]{40}$')

    def test_revision_mismatch_stops_before_preparation(self):
        result = self.command('--action', 'prepare-environment', '--board-id', 'esp32-devkit-v1',
                              '--expect-revision', '0' * 40)
        self.assertEqual(result.returncode, 1)
        value = json.loads(result.stdout)
        self.assertEqual(value['error'], 'source_revision_mismatch')
        self.assertFalse(value.get('installation_performed', False))

    def test_request_file_preserves_unicode_and_spaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / '中文 request.json'
            file.write_text(json.dumps({'board_id': 'unsupported-test', 'sketch': '中文 路径'}), encoding='utf-8-sig')
            result = self.command('--request-file', str(file), '--progress', 'none')
        self.assertEqual(result.returncode, 1)
        value = json.loads(result.stdout)
        self.assertEqual(value['state'], 'unsupported-board')
        self.assertIn('runtime', value)

