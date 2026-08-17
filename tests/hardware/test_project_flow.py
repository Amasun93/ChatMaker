import unittest

from chatmaker.hardware import project_flow


class FakeAdapter:
    def __init__(self, doctor, execution):
        self.doctor = doctor
        self.execution = execution
        self.requests = []

    def execute_request(self, request):
        self.requests.append(request)
        return self.doctor if request["action"] == "doctor" else self.execution


class FakeSerialManager:
    def __init__(self, *, matched=True):
        self.matched = matched
        self.closed = []

    def open(self, port, **options):
        return {"success": True, "session_id": "s1", "port": port, **options}

    def expect(self, session_id, marker, **options):
        return {"success": self.matched, "matched": self.matched, "marker": marker}

    def close(self, session_id):
        self.closed.append(session_id)
        return {"success": True, "session_id": session_id}


class ProjectFlowTests(unittest.TestCase):
    def run_with(self, execution, **request):
        adapter = FakeAdapter({"success": True, "ready_for_compile": True}, execution)
        serial = FakeSerialManager()
        result = project_flow.run_project(
            {"board_id": "arduino-nano-classic", "code": "void setup(){} void loop(){}", **request},
            adapters={"arduino-nano-classic": adapter},
            serial_manager=serial,
        )
        return result, adapter, serial

    def test_rejects_unsupported_board(self):
        result = project_flow.run_project({"board_id": "unknown", "code": "x"}, adapters={})
        self.assertEqual(result["state"], "unsupported-board")

    def test_stops_when_environment_is_missing(self):
        adapter = FakeAdapter({"success": False, "ready_for_compile": False}, {})
        result = project_flow.run_project(
            {"board_id": "arduino-nano-classic", "code": "x"},
            adapters={"arduino-nano-classic": adapter},
        )
        self.assertEqual(result["state"], "awaiting-environment")
        self.assertEqual(len(adapter.requests), 1)

    def test_compiles_then_waits_for_hardware(self):
        result, _, _ = self.run_with({"success": False, "stage": "awaiting-hardware"})
        self.assertEqual(result["state"], "compiled-awaiting-hardware")
        self.assertTrue(result["code_compiled"])
        self.assertFalse(result["firmware_uploaded"])

    def test_reports_compile_failure(self):
        result, _, _ = self.run_with({"success": False, "stage": "compile"})
        self.assertEqual(result["state"], "compile-failed")

    def test_upload_can_stop_at_user_observation(self):
        result, _, _ = self.run_with(
            {"success": True, "stage": "upload", "upload": {"port": "COM7"}},
            observe_serial=False,
        )
        self.assertEqual(result["state"], "uploaded-awaiting-observation")
        self.assertTrue(result["firmware_uploaded"])

    def test_serial_marker_still_requires_physical_confirmation(self):
        result, _, serial = self.run_with(
            {"success": True, "stage": "upload", "upload": {"port": "COM7"}},
            expected_serial_marker="READY",
        )
        self.assertEqual(result["state"], "physical-confirmation-needed")
        self.assertTrue(result["serial_evidence"]["matched"])
        self.assertEqual(serial.closed, ["s1"])


if __name__ == "__main__":
    unittest.main()
