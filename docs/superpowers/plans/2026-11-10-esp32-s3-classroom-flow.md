# ChatMaker independent classroom upload implementation plan

> For agentic workers: use superpowers:executing-plans in this session. User approved execution; routine implementation and verification proceed without another permission round.

**Goal:** Run supported hardware projects without making Mind+ a prerequisite, and add independently managed Waveshare ESP32-S3-Touch-LCD-2.8 V1/V2 software support.

**Architecture:** Keep exact board adapters. Add a small hardware workflow that prepares a missing supported environment once, compiles/uploads, and observes serial evidence. Add a separate Waveshare toolchain and adapter; fetch verified vendor drivers at runtime instead of redistributing them.

**Tech Stack:** Python 3.11, Arduino CLI 1.3.1, Arduino-ESP32 3.3.11 candidate (verify by real compilation), vendor LVGL 8.3.10 and revision-specific drivers.

**Spec:** `docs/superpowers/specs/2026-11-10-esp32-s3-classroom-flow-design.md`

**Software execution status:** complete on 2026-11-10. Final suite: 657 cases, 656 passed and one DOS-alias prerequisite skip; browser 5/5; doctor and Skills pass. Four example/revision compilations and a final compiler/cache reuse check passed. A fresh read-only review produced three Important findings and one unsupported-action documentation finding; all were addressed in one fix pass. Physical board and real WorkBuddy session acceptance remain pending, as detailed in the verification report.

## Global constraints

- Windows x64 first. No global PATH or AI host configuration changes.
- V1/V2 remains unknown for the user's physical board. Compile both separately; never infer upload identity from an ESP32-S3 chip or a COM port alone.
- First-use downloads are part of the approved local execution scope; use verified pinned assets and reuse them afterward.
- Distinguish software tests, real compilation, firmware upload, serial observation and physical effect.
- No push, release publication, or unrequested physical flash.

## Review focus

1. Missing or damaged cache must not be accepted as ready (task 2 integrity tests).
2. Unknown revision or ambiguous port must not write to hardware (task 2 target tests).
3. Repeated project execution must not reinstall tools (task 1 workflow tests).
4. Preparation/compiler failures must stop once with evidence, not cause alternate software installation (task 1 failure tests).
5. V2 vendor example contains CST3530 sources but still calls CST328: explicitly select corresponding driver, test transformation, compile both (task 2).

### Task 1: Independent execution flow

Files: `runtime/chatmaker/hardware/workflow.py`, `runtime/chatmaker/installers/local.py`, `pyproject.toml`, `skills/chatmaker/SKILL.md`, `skills/chatduino/SKILL.md`, `tests/hardware/test_workflow.py`, `tests/installers/test_local_installer.py`.

Produces: `workflow.run_project(request: dict, adapters: Mapping | None = None) -> dict`, CLI `chatmaker-hardware --request-json`. Adapters consume `doctor`, `prepare-environment`, `compile-upload` via `execute_request`.

- [x] Write/run failing behavior tests: reuse ready environment, prepare once when missing, stop on preparation failure, preserve missing-device/identity evidence, never turn local Mind+ absence into a mandatory installation.
- [x] Implement workflow and neutral capability guidance; update Skill routing to use it for existing managed boards and Waveshare. Preserve AVR/micro:bit-specific paths.
- [x] Run targeted tests and commit.

### Task 2: Waveshare managed adapter and examples

Files: `runtime/chatmaker/hardware/waveshare_s3.py`, `runtime/chatmaker/hardware/waveshare_toolchain.py`, `tests/hardware/test_waveshare_s3.py`, `examples/chatduino/waveshare-s3/`, canonical board/knowledge/recipe records and generated registry.

Produces: `waveshare_s3.execute_request(request: dict) -> dict`, `waveshare_toolchain.prepare_environment(revision: str) -> dict`, `context(revision: str) -> dict | None`, CLI `chatmaker-waveshare-s3`.

- [x] Write/run failing tests for unknown revision, exact target selection, no upload without identity, isolated flags, stale artifact rejection, vendor revision preparation and cache integrity.
- [x] Implement pinned Arduino CLI + isolated official core install and hash-verified vendor packages. Prepare minimal driver library and LVGL from vendor ZIPs. Apply documented deterministic V2 touch selection.
- [x] Implement compilation/upload and serial re-enumeration diagnostics, examples for screen diagnostic and touch timer, board/recipe/knowledge routing.
- [x] Real-compile both examples for V1/V2; record output sizes and hashes. Repeat environment preparation to verify reuse.
- [x] Run adapter/workflow/catalog tests and commit.

### Task 3: Repository and classroom verification

Files: installation/readme/update notes, `tests/release/test_clean_core_integration.py`, `docs/verification/2026-11-10-waveshare-s3-independent-flow.md`.

- [x] Correct stale release fixture without weakening catalog content checks; run full Python suite, runtime doctor, Skill validation and appropriate browser suite.
- [x] Inspect available WorkBuddy installation/execution surface and connected hardware; perform non-destructive host validation where available. Record missing prerequisites explicitly.
- [x] Fresh whole-branch review, address actionable findings, rerun affected checks.
- [x] Update source-backed verification report. Leave physical touch and reboot unverified unless actually observed on identified hardware.
