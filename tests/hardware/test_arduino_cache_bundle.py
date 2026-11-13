import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

from chatmaker.hardware import arduino_toolchain as chain
from chatmaker.hardware import arduino_cache_bundle as bundle


class ArduinoCacheBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.items = {}
        for name in ('compiler.zip', 'core.tar.gz', 'previous-compiler.zip'):
            payload = f'upstream archive {name}'.encode('ascii')
            archive = self.root / 'download-cache' / name
            archive.parent.mkdir(exist_ok=True)
            archive.write_bytes(payload)
            self.items[name] = {'filename': name, 'size': len(payload),
                                'sha256': hashlib.sha256(payload).hexdigest()}
        selected = ({'platform_tag': 'windows-amd64', 'artifacts': {
            'cli': self.items['compiler.zip'], 'core': self.items['core.tar.gz']},
            'fallback_cli': self.items['previous-compiler.zip']}, ['cli', 'core'])
        for patch in (
            mock.patch.object(chain, 'selected', return_value=selected),
            mock.patch.object(chain, 'archive_path', side_effect=lambda item: self.root / 'download-cache' / item['filename']),
        ):
            patch.start()
            self.addCleanup(patch.stop)

    def test_export_and_import_reuse_existing_verified_archive(self):
        output = self.root / 'avr-cache.zip'
        created = bundle.export_cache('avr', (), output)
        another = bundle.export_cache('avr', (), self.root / 'another.zip')
        self.assertEqual(created['size'], output.stat().st_size)
        self.assertEqual(created['sha256'], hashlib.sha256(output.read_bytes()).hexdigest())
        self.assertEqual(created['sha256'], another['sha256'])
        missing = self.root / 'download-cache' / 'core.tar.gz'
        missing.unlink()
        result = bundle.import_cache('avr', (), output)
        self.assertEqual(result['imported'], ['core.tar.gz'])
        self.assertEqual(result['reused'], ['compiler.zip'])
        self.assertEqual(hashlib.sha256(missing.read_bytes()).hexdigest(), self.items[missing.name]['sha256'])

    def test_import_checks_pinned_hash_before_replacing_an_archive(self):
        output = self.root / 'bad.zip'
        filename = 'compiler.zip'
        expected = (self.root / 'download-cache' / filename).read_bytes()
        with zipfile.ZipFile(output, 'w') as archive:
            archive.writestr(filename, b'x' * len(expected))
        with self.assertRaisesRegex(ValueError, 'cache_bundle_member_mismatch'):
            bundle.import_cache('avr', (), output)
        self.assertEqual((self.root / 'download-cache' / filename).read_bytes(), expected)

    def test_import_refuses_entries_outside_the_selected_toolchain(self):
        output = self.root / 'wrong.zip'
        with zipfile.ZipFile(output, 'w') as archive:
            archive.writestr('../compiler.zip', b'unsafe')
        with self.assertRaisesRegex(ValueError, 'cache_bundle_unexpected_member'):
            bundle.import_cache('avr', (), output)

    def test_export_preserves_previous_bundle_when_local_archive_is_missing(self):
        output = self.root / 'existing.zip'
        output.write_bytes(b'previous bundle')
        (self.root / 'download-cache' / 'core.tar.gz').unlink()
        with self.assertRaisesRegex(ValueError, 'verified_cache_archive_missing'):
            bundle.export_cache('avr', (), output)
        self.assertEqual(output.read_bytes(), b'previous bundle')

    def test_previous_cli_bundle_remains_importable(self):
        output = self.root / 'previous-cache.zip'
        (self.root / 'download-cache' / 'compiler.zip').unlink()
        result = bundle.export_cache('avr', (), output)
        self.assertIn('previous-compiler.zip', result['archives'])
        (self.root / 'download-cache' / 'previous-compiler.zip').unlink()
        result = bundle.import_cache('avr', (), output)
        self.assertIn('previous-compiler.zip', result['imported'])

    def test_import_does_not_promote_any_files_before_all_are_verified(self):
        output = self.root / 'partly-corrupt.zip'
        compiler = self.root / 'download-cache' / 'compiler.zip'
        core = self.root / 'download-cache' / 'core.tar.gz'
        with zipfile.ZipFile(output, 'w') as archive:
            archive.write(compiler, compiler.name)
            archive.writestr(core.name, b'x' * core.stat().st_size)
        compiler.unlink()
        core.unlink()
        with self.assertRaisesRegex(ValueError, 'cache_bundle_member_mismatch'):
            bundle.import_cache('avr', (), output)
        self.assertFalse(compiler.exists())
        self.assertFalse(core.exists())
