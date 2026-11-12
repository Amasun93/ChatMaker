import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

from chatmaker.hardware import workflow


class PreparationPreviewTests(unittest.TestCase):
    def test_classic_preview_is_read_only_and_selects_one_chip(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {'CHATMAKER_RUNTIME_ROOT': tmp + '/runtime'}):
            result = workflow.run_project({'action': 'prepare-environment', 'board_id': 'esp32-devkit-v1', 'dry_run': True})
            self.assertTrue(result['success'], result)
            self.assertFalse(Path(tmp, 'runtime').exists())
        names = [c['id'] for c in result['components']]
        self.assertIn('esp32-libs', names)
        self.assertNotIn('esp32s3-libs', names)
        self.assertNotIn('esp-rv32', names)
        self.assertLess(result['archive_bytes'], 800_000_000)


class ManagedArchiveTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.find_spec('chatmaker.hardware.arduino_toolchain')
        self.assertIsNotNone(spec, 'shared isolated Arduino preparation is missing')
        from chatmaker.hardware import arduino_toolchain
        self.chain = arduino_toolchain

    def test_zip_cannot_write_outside_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / 'tool.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('tool/../../escaped', 'bad')
            with self.assertRaises(ValueError):
                self.chain.extract_archive(archive, root / 'out', strip_root=True)
            self.assertFalse((root / 'escaped').exists())

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
