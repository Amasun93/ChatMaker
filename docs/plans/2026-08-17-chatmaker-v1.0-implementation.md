# ChatMaker V1.0 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Deliver a beginner-friendly creative partner that can progressively move from an idea to working hardware, optional web interaction, and optional laser-cut or 3D-printed enclosures.

**Architecture:** Keep ChatMaker as the conversation router. ChatDuino owns hardware, Mind+ compilation/upload and serial evidence; ChatWeb is loaded only when the user asks for a page or would benefit from one; ChatCAD routes fabrication to Chat2D laser cutting or Chat3D printing. Shared board, component, library, mechanical and fabrication facts remain in ChatMaker Knowledge.

**Tech Stack:** Python 3.11 runtime and MCP, Arduino C++, Mind+ 1.x/2.x toolchains for Nano/Uno, native HTML/CSS/JavaScript, OpenSCAD, SVG/DXF/STL, YAML/JSON knowledge packs.

---

## Product rules

- Start from the user's intended effect, not a mandatory technical checklist.
- Build the smallest observable hardware version first. Offer web or CAD as a later creative option, not a compulsory step.
- V1.0 flagship boards are Arduino Nano Classic, Arduino Uno R3 and Starcore v4.2.2. Existing ESP32 DevKit V1 support remains available but does not block release.
- Nano and Uno may reuse an existing Mind+ installation. A fully managed standalone AVR toolchain is post-V1.0.
- Keep environment, source, compile, upload, serial/browser and physical-effect evidence separate.
- During rapid development, run only the focused tests listed per task. Run one broader release check at the final V1.0 gate.

## V1.0 acceptance stories

1. Nano + sensor + OLED: generate wiring/code, resolve libraries, compile through Mind+, upload when one wired board exists, inspect serial evidence and ask for physical confirmation.
2. Uno + sensor/display or actuator: same continuous flow with Uno-specific board and upload settings.
3. Starcore + sensor + optional web page: compile/upload through a dedicated Starcore adapter, then demonstrate one real page-to-device exchange when hardware is available.
4. Chat2D: describe a laser-cut box, edit a white 2D canvas, place supported boards/modules, apply LaserMaker layers, preview the assembled box and export DXF/SVG.
5. Chat3D: describe a printable enclosure, adjust wall/holes/openings, rotate the preview and export OpenSCAD/STL.

### Task 1: Freeze the V1.0 experience contract

**Files:**
- Create: `docs/contracts/v1-creative-flow.md`
- Modify: `README.md`

**Steps:**
1. Describe the progressive conversation states and optional ChatWeb/ChatCAD branches.
2. Record the three flagship boards and Mind+ boundary.
3. Add the five acceptance stories and evidence states.
4. Check links and commit.

**Focused verification:** `python -m chatmaker.doctor`

### Task 2: Stabilize display libraries and representative AVR projects

**Files:**
- Create: `packs/recipes/nano-oled-dashboard.yaml`
- Create: `packs/recipes/uno-oled-dashboard.yaml`
- Create: `examples/chatduino/nano/oled-dashboard/oled-dashboard.ino`
- Create: `examples/chatduino/uno/oled-dashboard/oled-dashboard.ino`
- Modify: `packs/components/ssd1306-i2c-128x64-module.yaml`
- Modify: `packs/components/analog-light-sensor-module.yaml`
- Modify: `packs/components/momentary-button-two-pin.yaml`
- Modify: `packs/boards/arduino-uno-r3.yaml`
- Modify: `runtime/chatmaker/hardware/nano_examples.py`

**Steps:**
1. Add one readable dashboard behavior shared by Nano and Uno.
2. Record exact SSD1306/graphics library dependencies and safe I2C wiring.
3. Register both examples with their exact board targets.
4. Compile when a usable Mind+ toolchain is present; otherwise report `awaiting-toolchain` without pretending success.
5. Commit.

**Focused verification:** `python -m unittest tests.test_pack_validation tests.hardware.test_nano_examples -v`

### Task 3: Provide one continuous AVR project command

**Files:**
- Create: `runtime/chatmaker/hardware/project_flow.py`
- Modify: `runtime/chatmaker/integrations/workbuddy_mcp.py`
- Modify: `skills/chatduino/SKILL.md`
- Test: `tests/hardware/test_project_flow.py`

**Steps:**
1. Accept a board ID, source file and expected serial marker.
2. Route Nano or Uno to its existing prepare/compile/upload adapter.
3. Return one beginner-facing state: `awaiting-environment`, `compiled-awaiting-hardware`, `uploaded-awaiting-observation`, or `physical-confirmation-needed`.
4. Expose one MCP tool without removing the lower-level tools.
5. Commit after focused tests.

**Focused verification:** `python -m unittest tests.hardware.test_project_flow tests.integrations.test_workbuddy_mcp -v`

### Task 4: Add the Starcore executable path

**Files:**
- Create: `runtime/chatmaker/hardware/starcore.py`
- Modify: `runtime/chatmaker/integrations/workbuddy_mcp.py`
- Modify: `skills/chatduino/SKILL.md`
- Create: `examples/chatduino/starcore/blink/blink.ino`
- Test: `tests/hardware/test_starcore.py`

**Steps:**
1. Reuse the confirmed Mind+ 1.8 Starcore target and keep the historical 2.0 target separate.
2. Add discover, compile, safe upload and serial actions using existing adapter patterns.
3. Compile one minimal example when the toolchain is available.
4. Leave upload/runtime/physical states unverified until a real board is connected.
5. Commit.

**Focused verification:** `python -m unittest tests.hardware.test_starcore tests.integrations.test_workbuddy_mcp -v`

### Task 5: Add optional hardware web interaction

**Files:**
- Create: `runtime/chatmaker/web/device_contract.py`
- Create: `examples/chatweb/serial-device-console.html`
- Modify: `skills/chatweb/SKILL.md`
- Test: `tests/web/test_device_contract.py`

**Steps:**
1. Ask whether the user wants a page only after the basic hardware goal is clear or working.
2. Define one serial message contract for Nano/Uno and retain the existing HTTP route for Wi-Fi boards.
3. Generate one page with visible disconnected, connected, success and failure states.
4. Keep simulation visibly marked and separate from real exchange evidence.
5. Commit.

**Focused verification:** `python -m unittest tests.web.test_device_contract -v`

### Task 6: Deliver Chat2D and Chat3D V1.0 modes

**Files:**
- Create: `runtime/chatmaker/cad/chat2d.py`
- Create: `runtime/chatmaker/cad/chat3d.py`
- Modify: `runtime/chatmaker/cad/generator.py`
- Modify: `skills/chatcad/SKILL.md`
- Test: `tests/test_chat2d.py`
- Test: `tests/test_chat3d.py`

**Steps:**
1. Chat2D: generate a white editable laser-box canvas with adjustable dimensions and default 3 mm wood.
2. Place, drag, rotate and label supported board/module footprints; export LaserMaker-layered DXF/SVG.
3. Generate an assembled 3D preview from the flat laser-cut panels.
4. Chat3D: generate a printable enclosure with wall, lid, standoff and opening parameters.
5. Add mouse rotate/zoom/pan and export OpenSCAD/STL.
6. Commit after the two focused suites.

**Focused verification:** `python -m unittest tests.test_chat2d tests.test_chat3d -v`

### Task 7: V1.0 acceptance and release

**Files:**
- Modify: `README.md`
- Modify: `docs/installation.md`
- Create: `docs/verification/v1.0-acceptance.md`

**Steps:**
1. Record software evidence for all five acceptance stories.
2. Record hardware-dependent gates as verified only from real board results supplied by the user or colleague.
3. Run one consolidated focused suite covering installer, three board adapters, representative libraries, optional web and CAD modes.
4. Refresh global Skills, merge to `main`, push, and publish the V1.0 release only when required gates are met.

**Release verification:** one consolidated suite plus actual GitHub SHA/download checks; do not rerun unrelated historical stress suites.
