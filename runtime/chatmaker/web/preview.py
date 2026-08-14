from __future__ import annotations

import argparse
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urlsplit


@dataclass(frozen=True)
class PreviewAddress:
    host: str
    port: int
    url: str


def _handler_for(file: Path) -> type[BaseHTTPRequestHandler]:
    allowed_paths = {"/", f"/{quote(file.name)}"}

    class SingleFileHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            request_path = urlsplit(self.path).path
            if request_path == "/favicon.ico":
                self.send_response(204)
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                return
            if request_path not in allowed_paths:
                self.send_error(404, "Only the selected ChatWeb file is available")
                return
            try:
                payload = file.read_bytes()
            except OSError as exc:
                self.send_error(500, str(exc))
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            return

    return SingleFileHandler


def serve_preview(
    file: Path,
    host: str = "127.0.0.1",
    port: int = 0,
    allow_network: bool = False,
) -> tuple[ThreadingHTTPServer, PreviewAddress]:
    file = Path(file).resolve()
    if not file.is_file():
        raise FileNotFoundError(file)
    if file.suffix.casefold() not in {".html", ".htm"}:
        raise ValueError("ChatWeb preview requires an HTML file")
    if host not in {"127.0.0.1", "localhost"} and not allow_network:
        raise ValueError("non-loopback preview requires allow_network=True")

    server = ThreadingHTTPServer((host, port), _handler_for(file))
    thread = threading.Thread(target=server.serve_forever, name="chatmaker-web-preview", daemon=True)
    thread.start()
    bound_host, bound_port = server.server_address[:2]
    address = PreviewAddress(
        host=str(bound_host),
        port=int(bound_port),
        url=f"http://{bound_host}:{bound_port}/",
    )
    return server, address


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview one ChatWeb HTML file locally.")
    parser.add_argument("file", type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--allow-network", action="store_true")
    args = parser.parse_args()
    server, address = serve_preview(
        args.file,
        host=args.host,
        port=args.port,
        allow_network=args.allow_network,
    )
    print(f"ChatWeb preview: {address.url}", flush=True)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
