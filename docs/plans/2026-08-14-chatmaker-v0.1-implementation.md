# ChatMaker v0.1 Implementation Plan

> **For agentic workers:** Implement each phase with test-first changes and a fresh verification gate. Do not report hardware success without matching physical evidence.

**Goal:** Build an open-source AI-native maker workflow that lets beginners use natural language in Codex or WorkBuddy to create, compile, upload, observe, and verify simple hardware and native-web projects.

**Architecture:** Keep `chatmaker` as the thin creative-partner router, `chatduino` as the hardware workflow, and `chatweb` as the classroom-tool and hardware-interface workflow. Put deterministic operations in the shared Python runtime and put board, component, recipe, and UI knowledge in versioned data packs loaded only when needed.

**Tech Stack:** Python 3.11+, PyYAML, jsonschema, Arduino/Mind+ toolchains, serial ports, native HTML/CSS/JavaScript, unittest, GitHub Actions.

## Global Constraints

- Product name and GitHub repository name: `ChatMaker`; modules: `ChatDuino` and `ChatWeb`.
- Core experience: use natural language in an AI environment; do not build a separate IDE.
- v0.1 targets Windows x64, Arduino Uno R3, classic Arduino Nano ATmega328P, and ESP32 DevKit V1 / ESP-WROOM-32.
- Use an existing Mind+ 1.x or 2.x environment in the first release. Build a managed standalone toolchain in the next development phase.
- Keep environment discovery, compilation, upload, serial evidence, and physical-effect confirmation as separate truth gates.
- Never auto-upload when the connected board or port is ambiguous.
- Keep beginner wiring instructions in fenced plain-text blocks by default. SVG or other wiring graphics are optional extras, never a required first step.
- Start web work with native HTML, CSS, and JavaScript; no React, Vue, authentication, database, or cloud deployment in v0.1.
- Do not claim physical success from compilation, upload output, serial text, or a generated page alone.
- Keep the existing `arduino-nano-mindplus` repository unchanged until its behavior has been migrated and regression-tested here.

---

## File Map

- `skills/chatmaker/`: user-facing router and shared beginner workflow.
- `skills/chatduino/`: Arduino, Nano, ESP32, wiring, compile, upload, and serial workflow.
- `skills/chatweb/`: classroom tools, native web prototypes, and hardware-control interfaces.
- `runtime/chatmaker/`: deterministic Python APIs shared by Codex and WorkBuddy.
- `runtime/doctor.py`: command-line environment and pack diagnostics.
- `packs/schemas/`: JSON Schemas for versioned YAML records.
- `packs/boards/`, `packs/components/`, `packs/recipes/`: knowledge records and their evidence gates.
- `templates/`: output assets copied into user projects.
- `tests/`: runtime and contract tests.
- `docs/architecture/`: status model and subsystem boundaries.
- `docs/contributing/`: contribution contracts for board/component/recipe packs.

## Phase 1: Repository and Skill Foundation

**Output:** A local Git repository with Apache-2.0 licensing, bilingual entry documentation, CI, and three valid Skill folders.

**Acceptance:**

- `python .../quick_validate.py skills/<name>` passes for all three Skills.
- Each Skill contains only a concise `SKILL.md`, `agents/openai.yaml`, and resources it actually needs.
- `chatmaker` routes hardware and web requests without duplicating the specialist instructions.
- README status labels distinguish verified, partially verified, and planned support.

**Implementation steps:**

- [x] Initialize `main`, add `.gitignore`, Apache-2.0 `LICENSE`, `README.md`, and `README_EN.md`.
- [x] Run `init_skill.py` for `chatmaker`, `chatduino`, and `chatweb` with deterministic UI metadata.
- [x] Replace generated placeholders with router and specialist workflows.
- [x] Add `.github/workflows/ci.yml` that installs the package and runs all tests plus Skill validation.
- [x] Run local validation before creating the first commit.

## Phase 2: Versioned Data Packs and Evidence Model

**Output:** Executable schemas, a repository validator, and initial board/component/recipe records.

**Interfaces:**

```python
def load_record(path: Path) -> dict[str, object]: ...
def validate_record(record: dict[str, object], schema_dir: Path) -> list[str]: ...
def validate_repository(pack_root: Path, schema_dir: Path) -> ValidationReport: ...
```

**Acceptance:**

- Every record declares `schema_version`, `kind`, a stable `id`, sources, and the four evidence gates.
- `source_reviewed`, `code_compiled`, `firmware_uploaded`, and `physical_effect_verified` cannot collapse into one status.
- A `verified` gate requires both dated evidence and an evidence description.
- Duplicate record IDs, unknown references, and conflicting recipe pin assignments fail validation.
- Initial records cover Uno R3, Nano Classic, ESP32 DevKit V1, a basic LED, and Blink.

**Test cycle:**

- [x] Write tests for a valid repository, missing evidence, duplicate IDs, unknown references, and pin conflicts.
- [x] Run `python -m unittest discover -s tests -v`; confirm imports fail because the validator does not exist.
- [x] Implement schema loading and record validation.
- [x] Implement cross-record duplicate, reference, pin, source-file, and pin-conflict checks.
- [x] Add initial pack records with conservative status values and source links.
- [x] Run the full test suite and `python runtime/doctor.py --packs`.

## Phase 3: Migrate the Existing Nano Adapter

**Source:** `D:/Projects/26博荟暑假班/自研硬件Skill开发/05_发布包/arduino-nano-mindplus-github`

**Output:** A ChatDuino Nano adapter with behavior parity and explicit provenance.

**Interfaces:**

```python
def discover_nano_environment() -> EnvironmentReport: ...
def compile_nano(sketch: Path, environment: EnvironmentReport) -> CompileReport: ...
def upload_nano(hex_file: Path, candidate: PortCandidate) -> UploadReport: ...
```

**Acceptance:**

- Preserve Mind+ 1.x/2.x discovery, Bluetooth-port filtering, unique-device upload, 57600/115200 bootloader fallback, no-hardware waiting, and a maximum of two source repairs.
- Import the existing regression suite and six compile examples without lowering coverage.
- Treat the existing repository as read-only and copy only reviewed source files.
- Report environment, compilation, upload, serial evidence, and physical confirmation separately.

## Phase 4: Uno and ESP32 Adapters

**Output:** Separate board adapters and verified Blink matrices for Uno, Nano, and ESP32.

**Status:** Uno now has a separate Mind+ adapter, dedicated Blink example, Codex/WorkBuddy interfaces, fixed 115200 upload strategy, and a Mind+ 2.x compile result. Uno upload and physical gates remain open without hardware. ESP32 now has a strict DOIT DevKit V1 / ESP-WROOM-32 discovery, compile, and compile-upload contract locked to official `esp32:esp32@3.3.11` and `esp32:esp32:esp32doit-devkit-v1`. Upload is allowed only after the carrier board is explicitly confirmed and one wired, non-Bluetooth port remains. The local machine does not have the exact core, so no ESP32 example has been compiled or uploaded; FireBeetle and mPython remain rejected rather than treated as equivalents.

**Acceptance:**

- Uno reuses compatible AVR tooling without inheriting Nano upload parameters.
- ESP32 environment discovery proves the actual compiler, core, board ID, and libraries; Mind+ installation alone is not evidence.
- ESP32 3.3 V, input-only pins, strapping pins, and board-variant constraints are enforced.
- Each board progresses independently through compile, upload, reboot, and physical-effect gates.

## Phase 5: First Component Pack

**Output:** Versioned records and minimum examples for LED, RGB LED, button, light sensor, buzzer, HC-SR04, DHT11, SG90, SSD1306 OLED, relay, potentiometer, and WS2812.

**Status:** Implemented for all twelve planned component types. Ten Nano examples compile with Mind+ 2.x; upload and physical-effect gates remain independent and open without hardware.

**Acceptance:**

- Each record covers observable identification, pin labels, supply constraints, board differences, libraries, minimal code, common failures, sources, and evidence gates.
- Ambiguous modules remain unresolved until controller, interface, and voltage evidence is sufficient.
- High-current loads require an external supply and shared-ground guidance.

## Phase 6: Serial Monitor Runtime

**Output:** Structured serial tools exposed through the shared runtime.

**Status:** Implemented for WorkBuddy MCP and the Codex JSONL CLI. Automated
session lifecycle, empty-output, malformed-text, restart-loop, Bluetooth
rejection, and upload suspend/resume checks pass. Real Nano log evidence remains
open because no wired board is connected.

**Interfaces:**

```text
serial_list
serial_open
serial_read
serial_expect
serial_write
serial_close
```

**Acceptance:**

- Close serial handles before upload and reopen only after the board returns.
- Detect expected markers, watchdog messages, restart loops, malformed text, and timeouts.
- Empty serial output never becomes evidence of physical success.

## Phase 7: ChatWeb

**Output:** A mobile-first classroom and hardware-interface generator, local preview server, optional advanced playground, and browser verification workflow.

**Status:** The existing classroom and simulated-hardware pages have passed browser checks. The development branch also contains a self-contained mobile ESP32 AP control page with explicit real-device and simulation modes. Static contract tests cover touch sizing, connection states, same-origin API calls, and the rule that simulation never counts as hardware evidence. A real phone-to-device session is still unverified.

**Acceptance:**

- Generate a complete self-contained HTML/CSS/JavaScript project from a beginner request.
- Preview on localhost by default and expose network access only after an explicit request.
- Verify missing files, console errors, primary interactions, touch target size, and connection-state messaging.
- Report page rendering and interaction evidence separately from hardware connectivity.

## Phase 8: Flagship ESP32 AP Project

**Output:** An ESP32 access-point project served at `192.168.4.1` with LED control and sensor display.

**Status:** Firmware and page source now exist for a fixed beginner setup: external LED on GPIO23, 10 kOhm potentiometer on input-only GPIO34, SSID `ChatMaker-ESP32`, and same-origin `GET /`, `GET /api/state`, and `POST /api/led` routes. Automated source-contract tests pass. The required official ESP32 Core 3.3.11 is not installed, so compilation is unverified. No physical board is available, so upload, boot, SoftAP, HTTP round trips, LED control, potentiometer readings, serial logs, and power-cycle recovery all remain unverified.

**Acceptance:**

- A phone connects without school Wi-Fi, opens the page, controls the LED, and receives sensor data.
- Serial output records HTTP requests and device state.
- The complete flow survives power cycling.
- Wiring safety, firmware compile, upload, page load, controls, sensor reading, serial evidence, and physical confirmation are all recorded independently.

## Phase 9: Codex and WorkBuddy Installation

**Output:** Reversible installers plus a shared MCP/runtime configuration.

**Status:** The current development server exposes 23 WorkBuddy tools: 2 catalog tools, 5 Nano tools, 5 Uno tools, 5 ESP32 tools, and 6 serial tools. The fifth ESP32 tool is `esp32_compile_upload`; it preserves the board-identity, single-wired-port, Bluetooth-rejection, and separate-evidence gates. Codex and WorkBuddy were refreshed from the current repository, all three installed Skill hashes match, a real stdio smoke test lists all 23 tools, and five unrelated WorkBuddy MCP entries remain preserved. Host UI discovery still requires restarting the applications. This development count does not change the fixed rc4 release contents.

**Interfaces:**

```text
install_codex.py
install_workbuddy.py
doctor.py
```

**Acceptance:**

- Back up and merge existing configuration; never replace unrelated MCP settings.
- Detect Python, Mind+, Arduino CLI, browser, drivers, boards, and serial ports.
- Complete the same Nano Blink smoke test in Codex and WorkBuddy with equivalent structured reports.
- Installation success is never reported as hardware success.

## Phase 10: Public v0.1.0 Release

**Output:** Public repository, release archive, checksum, installation docs, contribution templates, and one-minute demo.

**Acceptance:**

- Windows hardware matrix passes for Uno, Nano, and ESP32.
- Ten to fifteen component records have reviewed sources and explicit evidence states.
- Native-web and ESP32 web-control flagship examples pass their full workflows.
- Codex and WorkBuddy installation tests pass on clean environments.
- GitHub Actions is green; release ZIP checksum is independently verified.

## Current Execution Boundary

Phase 1 and Phase 2 are complete. Phase 3 has migrated the reviewed Nano/Mind+
runtime, regression tests, WorkBuddy MCP bridge, and ten examples. All ten
examples compile from their new ChatMaker paths with Mind+ 2.x. The first
structured learning pack now maps those examples to twelve component records and
eleven recipes with identification, library, example, failure, and board notes.
Upload, serial, power-cycle, and physical-effect evidence remain open until a
wired Nano is available. ChatWeb single-file generation, localhost preview,
classroom interaction, and explicit hardware simulation have passed browser
verification. Reversible Codex and WorkBuddy installation plus live Blink
compile smoke tests have passed. The deterministic archive, checksum, clean
extraction test, GitHub rc2 tag, and two prerelease assets are complete. Host UI
discovery still requires restarting Codex and WorkBuddy; physical Nano gates
remain open until a wired board is available. The complete twelve-component
pack, ten compiled Nano examples, and catalog search/get interfaces are now
published in the rc3 tag and its two prerelease assets.

After the fixed rc4 release, the current development branch adds the strict
ESP32 compile-upload path and the flagship AP firmware/page pair. The
development WorkBuddy server definition now contains 23 tools (2 catalog, 5
Nano, 5 Uno, 5 ESP32, and 6 serial). A fresh Codex/WorkBuddy installation and
real stdio tool-list smoke check passed while preserving five unrelated MCP
entries; application restart and UI discovery remain open. The local machine still lacks the official ESP32 Core
3.3.11 and no physical DOIT board is connected, so ESP32 compilation, upload,
boot, SoftAP, HTTP, LED, potentiometer, serial, and power-cycle gates remain
unverified.
