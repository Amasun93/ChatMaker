import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock
from urllib.request import Request, urlopen

from chatmaker.installers import downloads
from chatmaker.progress import listening


class ResumableDownloadTests(unittest.TestCase):
    def setUp(self):
        self.payload = b'0123456789abcdef' * 10000
        self.ranges = []
        self.mode = 'interrupt-once'
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                value = self.headers.get('Range')
                owner.ranges.append(value)
                start = int(value.split('=')[1].split('-')[0]) if value else 0
                if owner.mode == 'ignore-range':
                    start = 0
                self.send_response(206 if start else 200)
                if start:
                    actual = start + 1 if owner.mode == 'wrong-range' else start
                    self.send_header('Content-Range', f'bytes {actual}-{len(owner.payload)-1}/{len(owner.payload)}')
                self.send_header('Content-Length', str(len(owner.payload) - start))
                self.end_headers()
                data = owner.payload[start:]
                if owner.mode == 'always-interrupt' or (owner.mode == 'interrupt-once' and len(owner.ranges) == 1):
                    data = data[:4096]
                self.wfile.write(data)
                self.close_connection = True

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.temp = tempfile.TemporaryDirectory()
        self.destination = Path(self.temp.name) / 'tool.zip'
        self.item = {'filename': 'tool.zip', 'size': len(self.payload),
                     'sha256': hashlib.sha256(self.payload).hexdigest(), 'sources': [
                         {'id': 'cn', 'kind': 'domestic_mirror', 'url': 'https://cn.example/tool.zip'},
                         {'id': 'fallback', 'kind': 'official_fallback', 'url': 'https://official.example/tool.zip'}]}
        def local_open(request, *, timeout, **kwargs):
            mapped = Request(f'http://127.0.0.1:{self.server.server_port}/tool', headers=dict(request.header_items()))
            return urlopen(mapped, timeout=timeout)
        self.patches = [mock.patch.object(downloads, 'urlopen', side_effect=local_open),
                        mock.patch.object(downloads, '_open_url', side_effect=local_open, create=True),
                        mock.patch.dict(os.environ, {'CHATMAKER_DOWNLOAD_POLICY': 'domestic-first', 'CHATMAKER_DOWNLOAD_MIRROR_BASE': ''})]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in reversed(self.patches):
            patch.stop()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def test_interruption_resumes_missing_bytes_and_reports_progress(self):
        events = []
        with listening(events.append):
            downloads.download_locked(self.item, self.destination)
        self.assertEqual(self.destination.read_bytes(), self.payload)
        self.assertEqual(self.ranges[:2], [None, 'bytes=4096-'])
        self.assertTrue(any(e['event'] == 'download_progress' for e in events))

    def test_failed_invocation_keeps_partial_for_next_invocation(self):
        self.mode = 'always-interrupt'
        with self.assertRaises(downloads.DownloadError):
            downloads.download_locked(self.item, self.destination)
        partial = self.destination.with_name('tool.zip.part')
        self.assertTrue(partial.exists())
        offset = partial.stat().st_size
        self.assertGreater(offset, 0)
        self.mode = 'normal'
        self.ranges.clear()
        downloads.download_locked(self.item, self.destination)
        self.assertEqual(self.ranges[0], f'bytes={offset}-')
        self.assertEqual(self.destination.read_bytes(), self.payload)

    def seed_partial(self):
        self.destination.with_name('tool.zip.part').write_bytes(self.payload[:4096])
        self.destination.with_name('tool.zip.part.json').write_text(json.dumps({
            'sha256': self.item['sha256'], 'size': self.item['size'], 'source_url': self.item['sources'][0]['url']}))

    def test_ignored_range_restarts_instead_of_appending_whole_file(self):
        self.seed_partial()
        self.mode = 'ignore-range'
        downloads.download_locked(self.item, self.destination)
        self.assertEqual(self.ranges[0], 'bytes=4096-')
        self.assertEqual(self.destination.read_bytes(), self.payload)

    def test_wrong_range_never_promotes_partial(self):
        self.seed_partial()
        self.mode = 'wrong-range'
        with self.assertRaises(downloads.DownloadError):
            downloads.download_locked(self.item, self.destination)
        self.assertFalse(self.destination.exists())

    def test_verified_cache_does_not_contact_any_source(self):
        self.destination.write_bytes(self.payload)
        result = downloads.download_locked(self.item, self.destination)
        self.assertFalse(result.changed)
        self.assertEqual(self.ranges, [])

    def test_corrupt_complete_partial_is_replaced_not_reused(self):
        self.seed_partial()
        self.destination.with_name('tool.zip.part').write_bytes(b'x' * len(self.payload))
        self.mode = 'normal'
        downloads.download_locked(self.item, self.destination)
        self.assertIsNone(self.ranges[0])
        self.assertEqual(self.destination.read_bytes(), self.payload)

    def test_domestic_redirect_is_rejected_before_requesting_foreign_host(self):
        guard = downloads._PolicyRedirect({'cn.example'})
        with self.assertRaisesRegex(downloads.DownloadError, 'blocked_by_policy'):
            guard.redirect_request(Request('https://cn.example/tool.zip'), None, 302, 'Found', {},
                                   'https://github.com/tool.zip')
