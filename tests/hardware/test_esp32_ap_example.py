from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKETCH_PATH = (
    ROOT
    / "examples"
    / "chatduino"
    / "esp32"
    / "ap-led-sensor"
    / "ap-led-sensor.ino"
)
PAGE_HEADER_PATH = SKETCH_PATH.with_name("page_html.h")
CHATWEB_PAGE_PATH = ROOT / "examples" / "chatweb" / "esp32-ap-control.html"


def embedded_page_from_header() -> str:
    header = PAGE_HEADER_PATH.read_text(encoding="utf-8") if PAGE_HEADER_PATH.is_file() else ""
    match = re.search(
        r'R"(?P<delimiter>[A-Z0-9_]+)\((?P<body>.*)\)(?P=delimiter)";',
        header,
        re.DOTALL,
    )
    return match.group("body") if match else ""


class Esp32ApExampleContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (
            SKETCH_PATH.read_text(encoding="utf-8") if SKETCH_PATH.is_file() else ""
        )

    def assert_source_matches(self, pattern: str, message: str) -> None:
        self.assertRegex(self.source, re.compile(pattern, re.DOTALL), message)

    def test_sketch_is_checked_in_at_the_documented_path(self):
        self.assertTrue(SKETCH_PATH.is_file(), f"missing ESP32 AP sketch: {SKETCH_PATH}")

    def test_soft_ap_uses_fixed_identity_and_network(self):
        self.assert_source_matches(
            r'AP_SSID\s*=\s*"ChatMaker-ESP32"\s*;',
            "SoftAP SSID must be ChatMaker-ESP32",
        )
        self.assert_source_matches(
            r"IPAddress\s+AP_IP\s*\(\s*192\s*,\s*168\s*,\s*4\s*,\s*1\s*\)\s*;",
            "SoftAP IP must be explicitly declared as 192.168.4.1",
        )
        self.assert_source_matches(
            r"WiFi\.softAPConfig\s*\(\s*AP_IP\s*,\s*AP_IP\s*,\s*AP_SUBNET\s*\)",
            "setup must explicitly configure the SoftAP IP, gateway, and subnet",
        )
        self.assert_source_matches(
            r"WiFi\.softAP\s*\(\s*AP_SSID\s*\)",
            "setup must start the named SoftAP",
        )

    def test_external_led_and_potentiometer_use_safe_fixed_pins(self):
        self.assert_source_matches(r"LED_PIN\s*=\s*23\s*;", "LED must use GPIO23")
        self.assert_source_matches(
            r"SENSOR_PIN\s*=\s*34\s*;", "10k potentiometer must use GPIO34"
        )
        self.assert_source_matches(
            r"pinMode\s*\(\s*LED_PIN\s*,\s*OUTPUT\s*\)",
            "external LED pin must be configured as an output",
        )
        self.assert_source_matches(
            r"analogRead\s*\(\s*SENSOR_PIN\s*\)",
            "state must sample the potentiometer input",
        )

    def test_routes_expose_html_state_and_led_control(self):
        self.assert_source_matches(
            r'server\.on\s*\(\s*"/"\s*,\s*HTTP_GET\s*,',
            "GET / route is missing",
        )
        self.assert_source_matches(
            r'server\.on\s*\(\s*"/api/state"\s*,\s*HTTP_GET\s*,',
            "GET /api/state route is missing",
        )
        self.assert_source_matches(
            r'server\.on\s*\(\s*"/api/led"\s*,\s*HTTP_POST\s*,',
            "POST /api/led route is missing",
        )
        self.assertIn('#include "page_html.h"', self.source)
        self.assert_source_matches(
            r'sendPageLogged\s*\(\s*\)',
            "GET / must serve the generated ChatWeb page",
        )

    def test_large_page_is_sent_from_progmem_without_a_temporary_string_copy(self):
        self.assert_source_matches(
            r"void\s+sendPageLogged\s*\(\s*\).*?server\.send_P\s*\(\s*200\s*,\s*PSTR\s*\(\s*\"text/html; charset=utf-8\"\s*\)\s*,\s*CHATMAKER_AP_PAGE\s*,\s*CHATMAKER_AP_PAGE_LENGTH\s*\)",
            "the generated phone page must stream from PROGMEM through send_P",
        )
        self.assertNotRegex(self.source, r"sendLogged\s*\([^;]*CHATMAKER_AP_PAGE")
        self.assertNotRegex(self.source, r"String\s*\(\s*CHATMAKER_AP_PAGE\s*\)")

    def test_state_json_has_the_stable_schema_and_live_values(self):
        for field in ("schema_version", "led_on", "sensor_raw", "uptime_ms"):
            self.assertIn(f'\\"{field}\\"', self.source, f"state JSON lacks {field}")
        self.assertIn('\\"schema_version\\":\\"1.0\\"', self.source)
        self.assert_source_matches(
            r"String\s+buildStateJson\s*\([^)]*\).*?analogRead\s*\(\s*SENSOR_PIN\s*\).*?millis\s*\(\s*\)",
            "state JSON must derive sensor_raw and uptime_ms from live readings",
        )
        self.assert_source_matches(
            r'sendLogged\s*\(\s*"GET"\s*,\s*"/api/state"\s*,\s*200\s*,\s*"application/json"\s*,\s*buildStateJson\s*\(\s*\)',
            "GET /api/state must return the latest JSON state",
        )

    def test_led_post_accepts_boolean_json_and_rejects_invalid_state(self):
        self.assert_source_matches(
            r'server\.arg\s*\(\s*"plain"\s*\)',
            "POST /api/led must inspect the JSON request body",
        )
        self.assertIn('{\\"on\\":true}', self.source)
        self.assertIn('{\\"on\\":false}', self.source)
        self.assert_source_matches(
            r'digitalWrite\s*\(\s*LED_PIN\s*,\s*requestedOn\s*\?\s*HIGH\s*:\s*LOW\s*\)',
            "a valid POST must apply the requested LED state",
        )
        self.assert_source_matches(
            r'sendLogged\s*\(\s*"POST"\s*,\s*"/api/led"\s*,\s*200\s*,\s*"application/json"\s*,\s*buildStateJson\s*\(\s*\)',
            "a valid POST must return the latest state",
        )
        self.assert_source_matches(
            r'sendLogged\s*\(\s*"POST"\s*,\s*"/api/led"\s*,\s*400\s*,\s*"application/json"\s*,\s*"\{\\\"error\\\":\\\"invalid_led_state\\\"\}"',
            "missing or invalid on must return the fixed 400 error",
        )

    def test_serial_logs_every_response_as_method_path_and_status(self):
        self.assert_source_matches(
            r"Serial\.begin\s*\(\s*115200\s*\)", "serial baud must be 115200"
        )
        self.assert_source_matches(
            r"void\s+sendLogged\s*\(.*?Serial\.print\s*\(\s*method\s*\).*?Serial\.print\s*\(\s*path\s*\).*?Serial\.println\s*\(\s*statusCode\s*\).*?server\.send\s*\(\s*statusCode",
            "response helper must log HTTP method, path, and status before sending",
        )

    def test_html_is_self_contained_and_calls_same_origin_apis(self):
        self.assertTrue(PAGE_HEADER_PATH.is_file(), "generated page_html.h is required")
        html = embedded_page_from_header()
        expected = CHATWEB_PAGE_PATH.read_text(encoding="utf-8")
        self.assertEqual(html, expected, "firmware page must exactly match the ChatWeb source")
        self.assertNotRegex(html, r"https?://|//cdn\.", "page must not use an external CDN")
        self.assertRegex(html, r"fetch\s*\(\s*['\"]\/api\/state['\"]")
        self.assertRegex(html, r"fetch\s*\(\s*['\"]\/api\/led['\"]")
        self.assertRegex(html, r"method\s*:\s*['\"]POST['\"]")
        self.assertRegex(html, r"Content-Type['\"]?\s*:\s*['\"]application/json['\"]")


if __name__ == "__main__":
    unittest.main()
