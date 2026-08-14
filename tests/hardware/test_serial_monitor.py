from __future__ import annotations

import sys
import json
import os
import subprocess
import unittest
from collections import deque
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.hardware.serial_monitor import SerialManager, analyze_lines  # noqa: E402


class FakeSerial:
    def __init__(self, *, port, baudrate, timeout, lines):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.lines = deque(lines)
        self.writes: list[bytes] = []
        self.is_open = True

    def readline(self):
        return self.lines.popleft() if self.lines else b""

    def write(self, payload):
        self.writes.append(payload)
        return len(payload)

    def flush(self):
        return None

    def close(self):
        self.is_open = False


class SerialMonitorTests(unittest.TestCase):
    def manager(self, lines=()):
        created: list[FakeSerial] = []

        def factory(**kwargs):
            handle = FakeSerial(lines=lines, **kwargs)
            created.append(handle)
            return handle

        ports = lambda: [
            {
                "address": "COM9",
                "is_bluetooth": False,
                "eligible_for_upload": True,
                "nano_likely": True,
            },
            {
                "address": "COM7",
                "is_bluetooth": True,
                "eligible_for_upload": False,
                "nano_likely": False,
            },
        ]
        return SerialManager(serial_factory=factory, port_provider=ports), created

    def test_open_expect_write_and_close_use_one_real_session(self):
        manager, created = self.manager([b"BOOT\r\n", b"NANO_BLINK_READY\r\n"])

        opened = manager.open("com9", baudrate=9600, timeout=0.01)
        expected = manager.expect(opened["session_id"], "NANO_BLINK_READY", timeout=0.05)
        written = manager.write(opened["session_id"], "LED_ON", newline=True)
        closed = manager.close(opened["session_id"])

        self.assertTrue(opened["success"])
        self.assertTrue(expected["success"], expected)
        self.assertEqual(expected["lines"], ["BOOT", "NANO_BLINK_READY"])
        self.assertEqual(written["bytes_written"], 7)
        self.assertEqual(created[0].writes, [b"LED_ON\n"])
        self.assertTrue(closed["success"])
        self.assertFalse(created[0].is_open)

    def test_empty_read_is_not_serial_evidence(self):
        manager, _ = self.manager()
        opened = manager.open("COM9", timeout=0.01)

        result = manager.read(opened["session_id"], timeout=0.02)

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "no_serial_output")
        self.assertFalse(result["serial_evidence"])

    def test_bluetooth_port_is_rejected(self):
        manager, created = self.manager()

        result = manager.open("COM7")

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "bluetooth_port_rejected")
        self.assertEqual(created, [])

    def test_serial_diagnostics_detect_malformed_text_and_restart_loops(self):
        diagnostics = analyze_lines(["ets Jan 8", "boot:0x13", "bad \ufffd text"])

        self.assertEqual(
            diagnostics,
            ["malformed_serial_text", "restart_loop_suspected"],
        )

    def test_jsonl_cli_lists_ports_for_codex(self):
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(ROOT / "runtime")
        completed = subprocess.run(
            [sys.executable, "-m", "chatmaker.hardware.serial_monitor"],
            input='{"action":"list"}\n',
            text=True,
            capture_output=True,
            cwd=ROOT,
            env=environment,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(completed.stdout.strip(), "serial JSONL CLI returned no response")
        result = json.loads(completed.stdout)
        self.assertTrue(result["success"])
        self.assertEqual(result["action"], "list")
        self.assertIn("ports", result)


if __name__ == "__main__":
    unittest.main()
