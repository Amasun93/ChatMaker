---
name: chatsim
description: Internal ChatMaker specialist for running compiled Arduino UNO R3 programs with virtual buttons, LEDs and an SSD1306 OLED in the browser.
---

# ChatSim

ChatSim is an internal specialist of ChatMaker. Use through `$chatmaker` to run a compiled Arduino UNO R3 sketch with virtual electronics inside the browser. Pick the circuit that matches the learner's requested electronics. Both circuits use an external normally open pushbutton from D2 to GND and configure D2 as `INPUT_PULLUP`.

| Circuit | Virtual output | Starter folder |
| --- | --- | --- |
| `button-led` (default) | D13 on while held, off when released | `examples/chatsim/uno-r3-button-led` |
| `button-oled` | SSD1306 128×64 I²C OLED at `0x3C`, SDA on A4, SCL on A5. Shows 再见 at rest, 你好 while held. | `examples/chatsim/uno-r3-button-oled` |

1. Have ChatDuino save the complete sketch in a folder with the same name as its main `.ino` file. For the OLED lesson, start from the included sketch. It uses the built-in Arduino Wire library and stores the four Chinese glyphs in the firmware.
2. Use `chatmaker-sim --sketch <sketch-folder> --circuit <circuit> --open` from the same checkout or installed Core as the Skill. The launcher prepares the managed UNO R3 compiler if needed. If the launcher is missing, run `-m chatmaker.sim` with the project Python or refresh the checkout runtime.
3. Verify the returned `preview.path`. If the default browser could not be launched, link to the generated HTML. The page comes prewired and includes the parts list. Tell the learner to click Run, then hold and release the red button (or focus it and hold Space). Report a simulated result after observing the chosen output in the browser. For real wiring with the OLED profile, use a module explicitly rated for 5 V power and I²C signals and match each pin by its printed label.

The OLED model supports the display RAM and basic SSD1306 commands used by the starter. ChatWeb handles webpages and control panels as projects in their own right. If the learner requests another board or peripheral, state the current simulation coverage. A ChatSim run verifies virtual behavior and needs no connected board. Verify voltage, wiring and the displayed result separately on real hardware.
