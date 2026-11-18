---
name: chatsim
description: Internal ChatMaker specialist for browser simulation of exact Arduino, ESP32 and Starcore boards using the bundled circuits and virtual components.
---

# ChatSim

ChatSim is an internal specialist of ChatMaker. Use through `$chatmaker`. Run `chatmaker-sim --list` to read the current boards, available parts and demos. Match the exact board and revision. A part marked `reference` has hardware information in the catalog, while `interactive` parts come with tested behavior in the listed demo. Review wiring in the existing ChatMaker Knowledge board and component cards.

For the Starcore v4.2.2 board and its classroom modules, run `chatmaker-sim --library starcore --open`. The gallery includes 22 component cards and two ready-to-run circuits. Explain the capabilities shown on the card to the student: interactive in an included experiment, appearance reference, or measured outline and mounting positions. Use the component card for wiring decisions, especially when any pin data is missing. Check `chatsim_version` and `runtime.source_commit` in `chatmaker-sim --version` if the gallery or example is missing.

| Demo ID | Board and controls | Execution |
| --- | --- | --- |
| `uno-r3-button-led` | UNO R3, D2 pushbutton and D13 LED | Compiled AVR firmware |
| `uno-r3-button-oled` | UNO R3, D2 pushbutton and SSD1306 I²C OLED | Compiled AVR firmware |
| `waveshare-v2-touch-greeting` | ESP32-S3-Touch-LCD-2.8 V2, hold the on-screen button | Shared LVGL interface compiled for the browser |
| `starcore-oled-greeting` | IDMC-0001 v4.2.2, hold the board's A key. IDMD-0021 OLED shows 你好 while held and 再见 at rest | Shared C logic compiled for the browser |
| `starcore-rgb-lab` | IDMC-0001 v4.2.2 with IDMS-0001 button, IDMS-0003 knob and IDMD-0001 RGB lamp. Hold to light up, turn the knob to change color, release to turn off | Shared C logic compiled for the browser |

1. Open an included example with `chatmaker-sim --demo <demo-id> --open` from the same Core as the Skill. These pages use already compiled programs and open directly. For a new UNO R3 sketch, have ChatDuino save it in a folder matching the main `.ino` filename. Use `chatmaker-sim --sketch <sketch-folder> --circuit button-led --open` or `--circuit button-oled`. Both use an active-low D2 switch to GND. The UNO R3 OLED uses A4/SDA, A5/SCL and a 5 V compatible SSD1306 module at `0x3C`.
2. Verify `preview.path`. Link to the generated HTML if browser dispatch is unavailable. UNO R3 learners select Run before pressing the red button. The Waveshare and Starcore demos start automatically. Report outcomes after observing them in the browser.
3. For the Starcore OLED circuit, use the board's A key and plug the IDMD-0021's complete four-wire cable into one 3V3 I²C socket. Keep P19/SCL, P20/SDA, power and ground in that socket. For the RGB lab, use verified 3V3 and GND. Connect button SIG to P8, knob SIG to P0, and RED/GREEN/BLUE to P9/P15/P23 on the S row. Browser connector positions are illustrative. Match the real labels before wiring. See the starter sources under `examples/chatsim` for hardware builds, shared logic and developer rebuild instructions.

For ESP32 and Starcore use the included code and its declared execution mode. Modified shared interface or logic requires a fresh browser build from the example sources. For hardware results, compile, upload and observe on the physical device separately with ChatDuino. ChatWeb handles projects whose product is a web page or control panel.

When adding a board, reuse the exact board/component IDs and their wiring references. Add the schematic outline, tested inputs and outputs, runnable example, execution mode and a hold/release or other observable test together. Keep parts whose behavior is still pending in `reference` status. In source checkouts the inventory lives in `runtime/chatmaker/sim_assets/catalog.json`.

When maintaining Starcore cards in source, register pins in `packs/components` and outlines and mounting holes in `knowledge/mechanical/components`. Run `python scripts/generate_chatsim_starcore_library.py` and add only reviewed appearance details. Keep the catalog IDs when connecting a part to a new executable example.
