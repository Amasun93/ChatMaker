import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock
from urllib.error import HTTPError, URLError
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

    def test_unavailable_artifact_immediately_tries_next_source(self):
        self.mode = 'normal'
        local_open = downloads._open_url.side_effect
        requested = []

        def open_from_source(request, **options):
            requested.append(request.host)
            if request.host == 'cn.example':
                raise HTTPError(request.full_url, 404, 'Not Found', {}, None)
            return local_open(request, **options)

        events = []
        with mock.patch.object(downloads, '_open_url', side_effect=open_from_source), listening(events.append):
            receipt = downloads.download_locked(self.item, self.destination)
        self.assertEqual(requested, ['cn.example', 'official.example'])
        self.assertEqual(receipt.source_id, 'fallback')
        self.assertEqual(self.destination.read_bytes(), self.payload)
        self.assertTrue(any(event['event'] == 'download_switch_source' for event in events))
        self.assertFalse(any(event['event'] == 'download_retry' for event in events))

    def test_connection_failure_reorders_later_components_in_the_same_session(self):
        self.mode = 'normal'
        local_open = downloads._open_url.side_effect
        requested = []

        def open_from_source(request, **options):
            requested.append(request.host)
            if request.host == 'cn.example':
                raise URLError(ConnectionRefusedError())
            return local_open(request, **options)

        with mock.patch.object(downloads, '_open_url', side_effect=open_from_source):
            with downloads.download_session():
                downloads.download_locked(self.item, self.destination)
                downloads.download_locked(self.item, self.destination.with_name('second.zip'))
            with downloads.download_session():
                downloads.download_locked(self.item, self.destination.with_name('third.zip'))
        self.assertEqual(requested, ['cn.example', 'official.example', 'official.example',
                                     'cn.example', 'official.example'])

    def test_slow_source_switches_and_backup_resumes_the_same_file(self):
        self.mode = 'normal'
        local_open = downloads._open_url.side_effect
        requested = []

        def open_from_source(request, **options):
            requested.append(request.host)
            return local_open(request, **options)

        events = []
        # The first source delivers 128 KiB in 30 seconds. Its remaining bytes
        # would take more than the threshold in this test. The backup is fast.
        with mock.patch.object(downloads, '_open_url', side_effect=open_from_source), \
             mock.patch.object(downloads, 'monotonic', side_effect=[0, 30, 31, 32], create=True), \
             mock.patch.object(downloads, 'SLOW_DOWNLOAD_ETA', 5, create=True), listening(events.append):
            receipt = downloads.download_locked(self.item, self.destination)
        self.assertEqual(requested, ['cn.example', 'official.example'])
        self.assertEqual(len(self.ranges), 2)
        progress = next(event for event in events if event['event'] == 'download_progress')
        self.assertGreater(progress['downloaded'], 0)
        self.assertEqual(self.ranges[1], f"bytes={progress['downloaded']}-")
        self.assertEqual(receipt.source_id, 'fallback')
        self.assertEqual(self.destination.read_bytes(), self.payload)
        self.assertEqual(next(e for e in events if e['event'] == 'download_switch_source')['reason'],
                         'download_too_slow')

    def test_single_source_remains_available_when_progress_is_slow(self):
        self.mode = 'normal'
        self.item['sources'].pop()
        with mock.patch.object(downloads, 'monotonic', side_effect=[0, 30, 60], create=True), \
             mock.patch.object(downloads, 'SLOW_DOWNLOAD_ETA', 5, create=True):
            receipt = downloads.download_locked(self.item, self.destination)
        self.assertEqual(receipt.source_id, 'cn')
        self.assertEqual(self.ranges, [None])

    def test_slow_source_is_resumed_when_the_backup_is_unavailable(self):
        self.mode = 'normal'
        local_open = downloads._open_url.side_effect

        def open_from_source(request, **options):
            if request.host == 'official.example':
                raise HTTPError(request.full_url, 404, 'Not Found', {}, None)
            return local_open(request, **options)

        with mock.patch.object(downloads, '_open_url', side_effect=open_from_source), \
             mock.patch.object(downloads, 'monotonic', side_effect=[0, 30, 31, 100]), \
             mock.patch.object(downloads, 'SLOW_DOWNLOAD_ETA', 5):
            receipt = downloads.download_locked(self.item, self.destination)
        self.assertEqual(receipt.attempted_source_ids, ('cn', 'fallback', 'cn'))
        self.assertEqual(self.destination.read_bytes(), self.payload)

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

    def test_strict_gitee_release_mirror_allows_its_attachment_host(self):
        self.mode = 'normal'
        with mock.patch.dict(os.environ, {
            'CHATMAKER_DOWNLOAD_POLICY': 'domestic-only',
            'CHATMAKER_DOWNLOAD_MIRROR_BASE': 'https://gitee.com/example/repo/releases/download/tools',
        }):
            receipt = downloads.download_locked(self.item, self.destination)
        request = downloads._open_url.call_args
        self.assertEqual(request.args[0].host, 'gitee.com')
        self.assertIn('foruda.gitee.com', request.kwargs['allowed_hosts'])
        self.assertNotIn('github.com', request.kwargs['allowed_hosts'])
        self.assertEqual(receipt.source_id, 'configured-domestic-mirror')
