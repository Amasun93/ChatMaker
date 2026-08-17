from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUTE_PATH = ROOT / "runtime" / "chatmaker" / "route.py"


def load_route():
    if not ROUTE_PATH.is_file():
        return None
    spec = importlib.util.spec_from_file_location("chatmaker_route", ROUTE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.route = load_route()

    def test_route_runtime_exists(self):
        self.assertIsNotNone(self.route, "chatmaker.route is missing")

    def test_hardware_intent_routes_to_chatduino(self):
        self.assertIsNotNone(self.route, "chatmaker.route is missing")

        result = self.route.execute_request(
            {
                "goal": "Blink a real LED from an Arduino Nano",
                "hardware": {
                    "board": "arduino-nano-classic",
                    "physical_effect": "The LED blinks on the desk.",
                },
            }
        )

        self.assertTrue(result["success"], result)
        self.assertEqual(result["route"], "hardware")
        self.assertEqual(result["stage"], "routed")
        self.assertEqual(result["specialists"], ["chatduino"])
        self.assertEqual(result["contract_requirements"], [])
        self.assertEqual(result["knowledge_requests"], [])

    def test_web_intent_routes_to_chatweb(self):
        self.assertIsNotNone(self.route, "chatmaker.route is missing")

        result = self.route.execute_request(
            {
                "goal": "Build a single-file classroom voting page",
                "web": {
                    "surface": "single-file-html",
                    "primary_interaction": "Tap one big answer button.",
                },
            }
        )

        self.assertTrue(result["success"], result)
        self.assertEqual(result["route"], "web")
        self.assertEqual(result["stage"], "routed")
        self.assertEqual(result["specialists"], ["chatweb"])
        self.assertEqual(result["knowledge_requests"], [])

    def test_ambiguous_intent_routes_to_clarify(self):
        self.assertIsNotNone(self.route, "chatmaker.route is missing")

        result = self.route.execute_request({"goal": "Make something interactive."})

        self.assertFalse(result["success"])
        self.assertEqual(result["route"], "clarify")
        self.assertEqual(result["stage"], "clarify")
        self.assertIn("hardware_web_or_cad_outcome", result["missing"])

    def test_cad_intent_routes_to_chatcad(self):
        result = self.route.execute_request(
            {"cad": {"board": "arduino-uno-r3", "outcome": "mounting plate"}}
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["route"], "cad")
        self.assertEqual(result["specialists"], ["chatcad"])
        self.assertTrue(result["evidence_boundaries"]["physical_fit_requires_separate_verification"])
        self.assertEqual(result["knowledge_requests"], [])

    def test_combined_intent_without_contract_stays_blocked_in_planning(self):
        self.assertIsNotNone(self.route, "chatmaker.route is missing")

        result = self.route.execute_request(
            {
                "goal": "Use a phone page to control an ESP32 LED.",
                "hardware": {
                    "board": "esp32-devkit-v1",
                    "physical_effect": "GPIO23 LED turns on and off.",
                },
                "web": {
                    "surface": "phone-web-page",
                    "primary_interaction": "Tap a toggle button.",
                },
            }
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["route"], "combined")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stage"], "planning")
        self.assertEqual(result["specialists"], ["chatduino", "chatweb"])
        self.assertEqual(
            result["contract_requirements"],
            ["transport", "request_response_or_message_interaction"],
        )
        self.assertEqual(result["knowledge_requests"], [])

    def test_combined_intent_with_contract_routes_without_promoting_web_to_hardware(self):
        self.assertIsNotNone(self.route, "chatmaker.route is missing")

        result = self.route.execute_request(
            {
                "goal": "Use a phone page to control an ESP32 LED.",
                "hardware": {
                    "board": "esp32-devkit-v1",
                    "physical_effect": "GPIO23 LED turns on and off.",
                },
                "web": {
                    "surface": "phone-web-page",
                    "primary_interaction": "Tap a toggle button.",
                    "render_status": "verified",
                },
                "communication_contract": {
                    "transport": "http",
                    "interactions": [
                        {
                            "request": "POST /api/led {\"on\": true}",
                            "response": "{\"ok\": true}",
                        }
                    ],
                },
            }
        )

        self.assertTrue(result["success"], result)
        self.assertEqual(result["route"], "combined")
        self.assertEqual(result["stage"], "routed")
        self.assertEqual(result["specialists"], ["chatduino", "chatweb"])
        self.assertTrue(result["evidence_boundaries"]["page_rendering_is_web_only"])
        self.assertTrue(
            result["evidence_boundaries"]["hardware_effect_requires_separate_verification"]
        )
        self.assertEqual(
            result["knowledge_requests"],
            [
                {
                    "action": "section",
                    "board_id": "esp32-devkit-v1",
                    "consumer": "chatweb",
                    "section_id": "web-and-protocol",
                }
            ],
        )

    def test_combined_intent_without_exact_board_identity_plans_no_knowledge_request(self):
        self.assertIsNotNone(self.route, "chatmaker.route is missing")

        requests = [
            {
                "goal": "Use a phone page to control an LED.",
                "hardware": {
                    "board": "esp32-devkit-v1-typo",
                    "physical_effect": "GPIO23 LED turns on and off.",
                },
                "web": {
                    "surface": "phone-web-page",
                    "primary_interaction": "Tap a toggle button.",
                },
                "communication_contract": {
                    "transport": "http",
                    "interactions": [
                        {
                            "request": "POST /api/led {\"on\": true}",
                            "response": "{\"ok\": true}",
                        }
                    ],
                },
            },
            {
                "goal": "Use a phone page to control an LED.",
                "hardware": {
                    "physical_effect": "GPIO23 LED turns on and off.",
                },
                "web": {
                    "surface": "phone-web-page",
                    "primary_interaction": "Tap a toggle button.",
                },
                "communication_contract": {
                    "transport": "http",
                    "interactions": [{"request": "GET /api/state", "response": "200 OK"}],
                },
            },
        ]

        for request in requests:
            with self.subTest(request=request):
                result = self.route.execute_request(request)
                self.assertTrue(result["success"], result)
                self.assertEqual(result["route"], "combined")
                self.assertEqual(result["knowledge_requests"], [])

    def test_combined_contract_rejects_non_string_or_blank_communication_fields(self):
        self.assertIsNotNone(self.route, "chatmaker.route is missing")
        invalid_values = [True, 7, {"value": "http"}, " \t\n"]
        base_request = {
            "hardware": {"board": "esp32-devkit-v1"},
            "web": {"surface": "phone-web-page"},
        }

        for invalid in invalid_values:
            with self.subTest(field="transport", value=invalid):
                result = self.route.execute_request(
                    {
                        **base_request,
                        "communication_contract": {
                            "transport": invalid,
                            "interactions": [
                                {"request": "GET /api/state", "response": "200 OK"}
                            ],
                        },
                    }
                )
                self.assertFalse(result["success"], result)
                self.assertIn("transport", result["contract_requirements"])
                self.assertEqual(result["knowledge_requests"], [])

        interaction_cases = {
            "request": lambda invalid: {
                "request": invalid,
                "response": "200 OK",
            },
            "response": lambda invalid: {
                "request": "GET /api/state",
                "response": invalid,
            },
            "message": lambda invalid: {"message": invalid},
        }
        for field, build_interaction in interaction_cases.items():
            for invalid in invalid_values:
                with self.subTest(field=field, value=invalid):
                    result = self.route.execute_request(
                        {
                            **base_request,
                            "communication_contract": {
                                "transport": "http",
                                "interactions": [build_interaction(invalid)],
                            },
                        }
                    )
                    self.assertFalse(result["success"], result)
                    self.assertIn(
                        "request_response_or_message_interaction",
                        result["contract_requirements"],
                    )
                    self.assertEqual(result["knowledge_requests"], [])

    def test_combined_contract_accepts_stripped_nonempty_communication_strings(self):
        self.assertIsNotNone(self.route, "chatmaker.route is missing")
        base_request = {
            "hardware": {"board": "esp32-devkit-v1"},
            "web": {"surface": "phone-web-page"},
        }
        interactions = [
            {"request": "  GET /api/state  ", "response": "  200 OK  "},
            {"message": "  led_state_changed  "},
        ]

        for interaction in interactions:
            with self.subTest(interaction=interaction):
                result = self.route.execute_request(
                    {
                        **base_request,
                        "communication_contract": {
                            "transport": "  http  ",
                            "interactions": [interaction],
                        },
                    }
                )
                self.assertTrue(result["success"], result)
                self.assertEqual(result["status"], "ready")
                self.assertEqual(
                    result["knowledge_requests"],
                    [
                        {
                            "action": "section",
                            "board_id": "esp32-devkit-v1",
                            "consumer": "chatweb",
                            "section_id": "web-and-protocol",
                        }
                    ],
                )

    def test_json_cli_routes_structured_intent(self):
        self.assertIsNotNone(self.route, "chatmaker.route is missing")
        environment = dict(os.environ)
        environment["PYTHONIOENCODING"] = "utf-8"

        completed = subprocess.run(
            [
                sys.executable,
                str(ROUTE_PATH),
                "--request-json",
                json.dumps(
                    {
                        "goal": "Build a single-file classroom voting page",
                        "web": {
                            "surface": "single-file-html",
                            "primary_interaction": "Tap one big answer button.",
                        },
                    }
                ),
            ],
            text=True,
            capture_output=True,
            cwd=ROOT,
            env=environment,
            timeout=10,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["success"], payload)
        self.assertEqual(payload["route"], "web")
        self.assertEqual(payload["knowledge_requests"], [])

    def test_json_cli_plans_only_web_and_protocol_for_exact_combined_board_identity(self):
        self.assertIsNotNone(self.route, "chatmaker.route is missing")
        environment = dict(os.environ)
        environment["PYTHONIOENCODING"] = "utf-8"

        completed = subprocess.run(
            [
                sys.executable,
                str(ROUTE_PATH),
                "--request-json",
                json.dumps(
                    {
                        "goal": "Use a phone page to control an ESP32 LED.",
                        "hardware": {
                            "board": "esp32-devkit-v1",
                            "physical_effect": "GPIO23 LED turns on and off.",
                        },
                        "web": {
                            "surface": "phone-web-page",
                            "primary_interaction": "Tap a toggle button.",
                        },
                        "communication_contract": {
                            "transport": "http",
                            "interactions": [
                                {
                                    "request": "POST /api/led {\"on\": true}",
                                    "response": "{\"ok\": true}",
                                }
                            ],
                        },
                    }
                ),
            ],
            text=True,
            capture_output=True,
            cwd=ROOT,
            env=environment,
            timeout=10,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["success"], payload)
        self.assertEqual(payload["route"], "combined")
        self.assertEqual(
            payload["knowledge_requests"],
            [
                {
                    "action": "section",
                    "board_id": "esp32-devkit-v1",
                    "consumer": "chatweb",
                    "section_id": "web-and-protocol",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
