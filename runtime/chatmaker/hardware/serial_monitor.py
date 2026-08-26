from __future__ import annotations

from dataclasses import dataclass
import argparse
import json
import sys
import time
from typing import Any, Callable
import uuid

from . import nano_mindplus


def _pyserial_factory(**kwargs: Any):
    import serial

    return serial.Serial(**kwargs)


def analyze_lines(lines: list[str]) -> list[str]:
    diagnostics: list[str] = []
    text = "\n".join(lines)
    if "\ufffd" in text:
        diagnostics.append("malformed_serial_text")
    normalized = [line.casefold().lstrip() for line in lines]
    ets_starts = sum(line.startswith("ets ") for line in normalized)
    reset_starts = sum(line.startswith(("rst:", "rst cause")) for line in normalized)
    restart_starts = max(ets_starts, reset_starts)
    if restart_starts >= 2:
        diagnostics.append("restart_loop_suspected")
    return diagnostics


@dataclass
class SerialSession:
    session_id: str
    port: str
    baudrate: int
    timeout: float
    handle: Any


class SerialManager:
    def __init__(
        self,
        *,
        serial_factory: Callable[..., Any] = _pyserial_factory,
        port_provider: Callable[[], list[dict[str, Any]]] = nano_mindplus.scan_ports,
    ) -> None:
        self.serial_factory = serial_factory
        self.port_provider = port_provider
        self.sessions: dict[str, SerialSession] = {}

    def list(self) -> dict[str, Any]:
        ports = self.port_provider()
        return {"success": True, "ports": ports, "open_sessions": list(self.sessions)}

    def open(self, port: str, baudrate: int = 9600, timeout: float = 0.1) -> dict[str, Any]:
        normalized = port.strip().upper() if port.strip().upper().startswith("COM") else port.strip()
        ports = self.port_provider()
        selected = next(
            (item for item in ports if str(item.get("address", "")).casefold() == normalized.casefold()),
            None,
        )
        if selected is None:
            return {"success": False, "error": "serial_port_not_currently_enumerated", "port": normalized}
        if selected.get("is_bluetooth"):
            return {"success": False, "error": "bluetooth_port_rejected", "port": normalized}
        if any(session.port.casefold() == normalized.casefold() for session in self.sessions.values()):
            return {"success": False, "error": "serial_session_already_open", "port": normalized}
        try:
            handle = self.serial_factory(port=normalized, baudrate=int(baudrate), timeout=float(timeout))
        except Exception as exc:
            return {
                "success": False,
                "error": "serial_open_failed",
                "detail": f"{type(exc).__name__}: {exc}",
                "port": normalized,
            }
        session_id = f"serial-{normalized.replace('/', '-')}-{uuid.uuid4().hex[:8]}"
        self.sessions[session_id] = SerialSession(
            session_id=session_id,
            port=normalized,
            baudrate=int(baudrate),
            timeout=float(timeout),
            handle=handle,
        )
        return {
            "success": True,
            "session_id": session_id,
            "port": normalized,
            "baudrate": int(baudrate),
        }

    def _session(self, session_id: str) -> SerialSession | None:
        return self.sessions.get(session_id)

    def read(
        self,
        session_id: str,
        *,
        timeout: float = 1.0,
        max_lines: int = 100,
    ) -> dict[str, Any]:
        session = self._session(session_id)
        if session is None:
            return {"success": False, "error": "serial_session_not_found", "session_id": session_id}
        deadline = time.monotonic() + max(0.0, min(float(timeout), 60.0))
        limit = max(1, min(int(max_lines), 500))
        lines: list[str] = []
        try:
            while len(lines) < limit and time.monotonic() <= deadline:
                raw = session.handle.readline()
                if raw:
                    if isinstance(raw, bytes):
                        text = raw.decode("utf-8", errors="replace")
                    else:
                        text = str(raw)
                    lines.append(text.rstrip("\r\n"))
                    continue
                remaining = deadline - time.monotonic()
                if remaining > 0:
                    time.sleep(min(0.01, remaining))
        except Exception as exc:
            return {
                "success": False,
                "error": "serial_read_failed",
                "detail": f"{type(exc).__name__}: {exc}",
                "session_id": session_id,
                "lines": lines,
                "serial_evidence": bool(lines),
            }
        return {
            "success": bool(lines),
            "error": None if lines else "no_serial_output",
            "session_id": session_id,
            "port": session.port,
            "lines": lines,
            "diagnostics": analyze_lines(lines),
            "serial_evidence": bool(lines),
        }

    def expect(
        self,
        session_id: str,
        marker: str,
        *,
        timeout: float = 5.0,
        max_lines: int = 200,
    ) -> dict[str, Any]:
        result = self.read(session_id, timeout=timeout, max_lines=max_lines)
        lines = result.get("lines", [])
        matched = any(marker in line for line in lines)
        return {
            **result,
            "success": matched,
            "error": None if matched else (result.get("error") or "serial_marker_not_seen"),
            "marker": marker,
            "matched": matched,
        }

    def write(self, session_id: str, text: str, *, newline: bool = False) -> dict[str, Any]:
        session = self._session(session_id)
        if session is None:
            return {"success": False, "error": "serial_session_not_found", "session_id": session_id}
        payload = (text + ("\n" if newline else "")).encode("utf-8")
        try:
            written = int(session.handle.write(payload))
            if hasattr(session.handle, "flush"):
                session.handle.flush()
        except Exception as exc:
            return {
                "success": False,
                "error": "serial_write_failed",
                "detail": f"{type(exc).__name__}: {exc}",
                "session_id": session_id,
            }
        return {"success": True, "session_id": session_id, "bytes_written": written}

    def close(self, session_id: str) -> dict[str, Any]:
        session = self.sessions.pop(session_id, None)
        if session is None:
            return {"success": False, "error": "serial_session_not_found", "session_id": session_id}
        try:
            session.handle.close()
        except Exception as exc:
            return {
                "success": False,
                "error": "serial_close_failed",
                "detail": f"{type(exc).__name__}: {exc}",
                "session_id": session_id,
            }
        return {"success": True, "session_id": session_id, "port": session.port}

    def suspend_all(self) -> list[dict[str, Any]]:
        settings = [
            {"port": session.port, "baudrate": session.baudrate, "timeout": session.timeout}
            for session in self.sessions.values()
        ]
        for session_id in list(self.sessions):
            self.close(session_id)
        return settings

    def resume_all(self, settings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [self.open(**setting) for setting in settings]


SERIAL_MANAGER = SerialManager()


def execute_request(request: dict[str, Any], manager: SerialManager = SERIAL_MANAGER) -> dict[str, Any]:
    action = request.get("action")
    if action == "list":
        result = manager.list()
    elif action == "open":
        result = manager.open(
            str(request.get("port", "")),
            baudrate=int(request.get("baudrate", 9600)),
            timeout=float(request.get("timeout", 0.1)),
        )
    elif action == "read":
        result = manager.read(
            str(request.get("session_id", "")),
            timeout=float(request.get("timeout", 1)),
            max_lines=int(request.get("max_lines", 100)),
        )
    elif action == "expect":
        result = manager.expect(
            str(request.get("session_id", "")),
            str(request.get("marker", "")),
            timeout=float(request.get("timeout", 5)),
            max_lines=int(request.get("max_lines", 200)),
        )
    elif action == "write":
        result = manager.write(
            str(request.get("session_id", "")),
            str(request.get("text", "")),
            newline=bool(request.get("newline", False)),
        )
    elif action == "close":
        result = manager.close(str(request.get("session_id", "")))
    else:
        return {"action": action, "success": False, "error": "unknown_serial_action"}
    return {"action": action, **result}


def _safe_execute(raw: str) -> dict[str, Any]:
    try:
        request = json.loads(raw)
        if not isinstance(request, dict):
            raise ValueError("request must be an object")
        return execute_request(request)
    except Exception as exc:
        return {
            "success": False,
            "error": "serial_request_failed",
            "detail": f"{type(exc).__name__}: {exc}",
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Persistent JSONL serial monitor for ChatMaker.")
    parser.add_argument("--request-json")
    args = parser.parse_args(argv)
    if args.request_json is not None:
        result = _safe_execute(args.request_json)
        print(json.dumps(result, ensure_ascii=False))
        SERIAL_MANAGER.suspend_all()
        return 0 if result.get("success") else 1

    exit_code = 0
    try:
        for raw in sys.stdin:
            if not raw.strip():
                continue
            result = _safe_execute(raw)
            sys.stdout.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
            sys.stdout.flush()
            if not result.get("success") and result.get("error") not in {
                "no_serial_output",
                "serial_marker_not_seen",
            }:
                exit_code = 1
    finally:
        SERIAL_MANAGER.suspend_all()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
