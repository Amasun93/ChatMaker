import base64
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from chatmaker import sim
from chatmaker.route import execute_request
from chatmaker.sim_catalog import load_catalog


class ChatSimTests(unittest.TestCase):
    def test_compiler_output_drives_preview_without_an_upload_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            source = root / "button"
            source.mkdir()
            (source / "button.ino").write_text("void setup() {} void loop() {}")
            build = root / "build"
            build.mkdir()
            plain_hex = b":02000000259A3F\n:00000001FF\n"
            (build / "button.ino.hex").write_bytes(plain_hex)
            (build / "button.ino.with_bootloader.hex").write_bytes(b"not the sketch")
            result = {"success": True, "compile": {"build_path": str(build)}}
            with patch.object(sim, "run_project", side_effect=[
                {"ready_for_compile": True}, result,
            ]) as run, patch.object(sim.webbrowser, "open", return_value=True) as browse:
                preview = sim.run_simulation(source, runtime_root=root, output=None, open_browser=True)
            self.assertEqual([call.args[0]["action"] for call in run.call_args_list], ["doctor", "compile"])
            self.assertTrue(preview["code_compiled"])
            self.assertFalse(preview["firmware_uploaded"])
            self.assertEqual(preview["preview"]["firmware_sha256"], sha256(plain_hex).hexdigest())
            html = Path(preview["preview"]["path"]).read_text(encoding="utf-8")
            self.assertIn(base64.b64encode(b"\x25\x9a").decode(), html)
            browse.assert_called_once_with(preview["preview"]["url"], new=2)

    def test_corrupted_hex_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid_avr_hex_checksum"):
            sim.read_avr_hex(":02000000259A00\n:00000001FF\n")

    def test_oled_circuit_embeds_its_peripheral_in_the_generated_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            firmware = root / "button.ino.hex"
            firmware.write_bytes(b":02000000259A3F\n:00000001FF\n")
            preview = sim.render_preview(firmware, runtime_root=root, output=None, circuit="button-oled")
            html = Path(preview["path"]).read_text(encoding="utf-8")
            self.assertIn('data-circuit="button-oled"', html)
            self.assertIn('class ChatSimSSD1306', html)
            self.assertIn('data-board-pin="A4" data-oled-pin="SDA"', html)

    def test_simulation_routes_exact_models_and_checks_waveshare_revision(self):
        uno = execute_request({"simulation": True, "hardware": {"board": "arduino-uno-r3"}})
        self.assertTrue(uno["success"])
        self.assertEqual(uno["specialists"], ["chatduino", "chatsim"])
        r4 = execute_request({"simulation": True, "hardware": {"board": "arduino-uno-r4-wifi"}})
        self.assertFalse(r4["success"])
        self.assertIn("arduino-uno-r3", r4["supported_boards"])
        self.assertNotIn("arduino-uno-r4-wifi", r4["supported_boards"])
        starcore = execute_request({"simulation": True, "hardware": {"board": "idmc-0001-starcore-v4-2-2"}})
        self.assertTrue(starcore["success"])
        self.assertEqual([demo["id"] for demo in starcore["demos"]], ["starcore-oled-greeting", "starcore-rgb-lab"])
        self.assertEqual({demo["mode"] for demo in starcore["demos"]}, {"program-logic"})
        self.assertEqual(starcore["libraries"], ["starcore"])
        for revision in (None, "v1", "v2"):
            request = {"simulation": True, "hardware": {"board": "waveshare-esp32-s3-touch-lcd-2-8",
                                                        "revision": revision}}
            result = execute_request(request)
            self.assertEqual(result["success"], revision == "v2")
            if revision == "v2":
                self.assertEqual([demo["mode"] for demo in result["demos"]], ["interface"])
            else:
                self.assertEqual(result["required_revision"], "v2")

    def test_bundled_demos_open_without_preparation_or_compilation(self):
        catalog = load_catalog()
        self.assertEqual({item["series"] for item in catalog["boards"]}, {"arduino", "esp32", "starcore"})
        with tempfile.TemporaryDirectory() as tmp, patch.object(sim, "run_project") as hardware:
            root = Path(tmp).resolve()
            for demo in catalog["demos"]:
                with self.subTest(demo=demo["id"]):
                    for part in demo["parts"]:
                        self.assertEqual(catalog["parts"][part]["availability"], "interactive")
                    result = sim.run_demo(demo["id"], runtime_root=root, output=None, open_browser=False)
                    self.assertTrue(result["success"], result)
                    self.assertTrue(result["uses_precompiled_program"])
                    self.assertFalse(result["code_compiled"])
                    self.assertFalse(result["firmware_uploaded"])
                    self.assertEqual(result["simulation_mode"], demo["mode"])
                    self.assertTrue(Path(result["preview"]["path"]).is_file())
            hardware.assert_not_called()
