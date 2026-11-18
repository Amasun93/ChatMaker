---
name: chatsim
description: Internal ChatMaker specialist for running compiled Arduino UNO R3 button-and-LED programs in a browser with ChatSim.
---

# ChatSim

ChatSim is an internal specialist of ChatMaker. Use through `$chatmaker`. The first classroom circuit is Arduino UNO R3, a normally open pushbutton from D2 to GND, and the board's D13 LED. The sketch uses `INPUT_PULLUP`, so pressing the button reads LOW.

1. Have ChatDuino save the learner's complete Arduino sketch in a folder with the same name as its main `.ino` file. For the starter, use `examples/chatsim/uno-r3-button-led` in the ChatMaker checkout.
2. Run the launcher from the same ChatMaker checkout or installed Core as the Skill. Use `chatmaker-sim --sketch <sketch-folder> --open`. This uses the managed Uno R3 compiler, prepares it if needed, and opens a self-contained HTML preview. If the newly updated checkout lacks the launcher, use its existing project Python with `-m chatmaker.sim` or refresh the checkout runtime. No extra browser package or IDE is needed for the student.
3. Verify the returned `preview.path`. If the default browser could not be launched, offer the generated HTML as a link. Point out the labelled UNO R3 and pushbutton. The learner clicks D2 and one button terminal, then GND and the other terminal. Only report a simulated press/LED result after seeing it in the browser. After both wires are connected, the example should light while the button is held and turn off on release. Use Clear Wiring to try again.

Use this route for the UNO R3 circuit above. If the learner requests a different board or virtual peripherals, state the current simulation coverage and offer the relevant ChatDuino workflow or a labelled interaction preview via ChatWeb. Keep simulation evidence separate from observed physical results. The simulation route does not require a USB device, board identification probe, or upload.
