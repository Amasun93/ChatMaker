import unittest
from pathlib import Path

from chatmaker.web.device_contract import contract_summary, decode_line, encode_message


ROOT = Path(__file__).resolve().parents[2]


class DeviceContractTests(unittest.TestCase):
    def test_browser_command_round_trips_as_json_line(self):
        encoded = encode_message({"type": "command", "target": "led", "value": True}, sender="browser")
        self.assertTrue(encoded.endswith(b"\n"))
        self.assertTrue(decode_line(encoded, sender="browser")["value"])

    def test_device_telemetry_requires_sensor_name(self):
        with self.assertRaisesRegex(ValueError, "sensor_required"):
            encode_message({"type": "telemetry", "value": 42}, sender="device")

    def test_contract_is_versioned(self):
        summary = contract_summary()
        self.assertEqual(summary["version"], 1)
        self.assertIn("command", summary["browser_to_device"])

    def test_example_distinguishes_real_and_simulated_connection(self):
        text = (ROOT / "examples/chatweb/serial-device-console.html").read_text(encoding="utf-8")
        self.assertIn("navigator.serial.requestPort", text)
        self.assertIn("模拟设备已连接（不代表真实硬件）", text)
        self.assertIn("设备未连接", text)
        self.assertIn("连接失败", text)
        self.assertIn("min-height:48px", text)


if __name__ == "__main__":
    unittest.main()
