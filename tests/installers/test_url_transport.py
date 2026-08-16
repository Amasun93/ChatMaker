from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
from pathlib import Path
import sys
import threading
import time
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

try:
    from chatmaker.installers.pack_manager import (
        StreamResponse,
        TransportError,
        UrlTransport,
    )
except ImportError:
    StreamResponse = None
    TransportError = None
    UrlTransport = None


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
        self.server.calls.append(self.path)  # type: ignore[attr-defined]
        route = self.server.routes[self.path]  # type: ignore[attr-defined]
        route(self)

    def log_message(self, format: str, *args) -> None:
        return


class _Server:
    def __init__(self) -> None:
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.httpd.routes = {}  # type: ignore[attr-defined]
        self.httpd.calls = []  # type: ignore[attr-defined]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    @property
    def base_url(self) -> str:
        host, port = self.httpd.server_address
        return f"http://{host}:{port}"

    @property
    def calls(self) -> list[str]:
        return self.httpd.calls  # type: ignore[attr-defined]

    def route(self, path: str, callback) -> None:
        self.httpd.routes[path] = callback  # type: ignore[attr-defined]

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)


def _bytes(payload: bytes):
    def send(handler: BaseHTTPRequestHandler) -> None:
        handler.send_response(200)
        handler.send_header("Content-Length", str(len(payload)))
        handler.end_headers()
        handler.wfile.write(payload)

    return send


def _redirect(location: str):
    def send(handler: BaseHTTPRequestHandler) -> None:
        handler.send_response(302)
        handler.send_header("Location", location)
        handler.send_header("Content-Length", "0")
        handler.end_headers()

    return send


class UrlTransportLoopbackTests(unittest.TestCase):
    def setUp(self) -> None:
        if UrlTransport is None or TransportError is None or StreamResponse is None:
            self.fail("bounded UrlTransport is missing")
        self.servers: list[_Server] = []

    def tearDown(self) -> None:
        for server in reversed(self.servers):
            server.close()

    def server(self) -> _Server:
        server = _Server()
        self.servers.append(server)
        return server

    def assert_transport_reason(self, reason: str, operation, *args, **kwargs):
        with self.assertRaises(TransportError) as caught:
            operation(*args, **kwargs)
        self.assertEqual(caught.exception.reason, reason)
        return caught.exception

    def test_same_origin_redirect_is_followed_under_one_byte_ceiling(self):
        server = self.server()
        server.route("/redirect", _redirect("/payload"))
        server.route("/payload", _bytes(b"registry"))

        response = UrlTransport(timeout=1).fetch(
            server.base_url + "/redirect", max_bytes=8
        )

        self.assertEqual(response.data, b"registry")
        self.assertEqual(response.final_url, server.base_url + "/payload")
        self.assertEqual(server.calls, ["/redirect", "/payload"])

    def test_different_origin_redirect_is_rejected_before_target_contact(self):
        origin = self.server()
        target = self.server()
        origin.route("/redirect", _redirect(target.base_url + "/secret"))
        target.route("/secret", _bytes(b"must not be contacted"))

        self.assert_transport_reason(
            "redirect_origin_changed",
            UrlTransport(timeout=1).fetch,
            origin.base_url + "/redirect",
            max_bytes=64,
        )

        self.assertEqual(origin.calls, ["/redirect"])
        self.assertEqual(target.calls, [])

    def test_registry_signature_and_streamed_pack_limits_stop_at_limit_plus_one(self):
        server = self.server()
        server.route("/registry", _bytes(b"r" * 9))
        server.route("/signature", _bytes(b"s" * 9))
        server.route("/pack", _bytes(b"p" * 9))
        transport = UrlTransport(timeout=1)

        for path in ("/registry", "/signature"):
            with self.subTest(path=path):
                self.assert_transport_reason(
                    "response_too_large",
                    transport.fetch,
                    server.base_url + path,
                    max_bytes=8,
                )

        sink = io.BytesIO()
        self.assert_transport_reason(
            "response_too_large",
            transport.fetch_to,
            server.base_url + "/pack",
            sink,
            max_bytes=8,
        )
        self.assertLessEqual(len(sink.getvalue()), 8)

    def test_overall_deadline_bounds_a_slow_body(self):
        server = self.server()

        def slow(handler: BaseHTTPRequestHandler) -> None:
            handler.send_response(200)
            handler.send_header("Content-Length", "2")
            handler.end_headers()
            handler.wfile.write(b"a")
            handler.wfile.flush()
            time.sleep(0.25)
            try:
                handler.wfile.write(b"b")
            except (BrokenPipeError, ConnectionResetError):
                pass

        server.route("/slow", slow)

        started = time.monotonic()
        self.assert_transport_reason(
            "deadline_exceeded",
            UrlTransport(timeout=0.05).fetch,
            server.base_url + "/slow",
            max_bytes=8,
        )
        self.assertLess(time.monotonic() - started, 0.2)


if __name__ == "__main__":
    unittest.main()
