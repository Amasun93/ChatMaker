# ChatMaker v0.1.0-rc5 Implementation Plan

## Goal

Turn the current public-main development capabilities into a reviewable rc5 candidate while closing the software-only evidence gaps found in the 2026-08-15 completion audit. Physical-board gates remain explicitly unverified.

## Global Constraints

- Preserve the public product names ChatMaker, ChatDuino, and ChatWeb.
- Do not modify `Amasun93/arduino-nano-mindplus` or its local checkout.
- Nano and Uno continue to reuse Mind+ 1.x/2.x in v0.1; the standalone toolchain is a later phase.
- ESP32 accepts only official `esp32:esp32@3.3.11` and `esp32:esp32:esp32doit-devkit-v1`; never use a Mind+ CLI for ESP32.
- Wiring defaults to a fenced `text` block. SVG remains opt-in.
- Keep environment, source, compile, upload, serial/browser, network, power-cycle, and physical-effect evidence separate.
- Beginner ChatWeb defaults to two or three curated directions. Extra directions and the playground appear only through an explicit advanced request.
- Native HTML/CSS/JavaScript only; no cloud, database, authentication, React, or Vue.
- Use test-first changes. Never claim real-device success without matching physical evidence.

## Task 1: Close Nano migration evidence and upload-safety gaps

### Requirements

- Update the Nano board evidence and migration manifest so they distinguish the six original v1.2 examples from the current ten compile-verified ChatMaker examples.
- Record the read-only source checkout evidence: commit `9ebc6bff16529557aa2cebe661755cf6c51d79ed`, clean status at audit time, and no source write performed.
- Add an explicit one-to-one mapping for all 33 legacy tests: 25 Nano runtime tests, 3 WorkBuddy/installer tests, and 5 teacher-experience tests. Preserve the current target test paths.
- Add end-to-end upload-result tests proving that a compiled sketch never invokes avrdude when there are multiple ambiguous wired ports or when an explicitly requested port is Bluetooth.
- The tests must exercise `upload_result` or the real compile-upload composition, not only `select_upload_port` in isolation.
- Do not change runtime behavior unless a failing test reveals a real defect.

### Verification

- Run the focused Nano, WorkBuddy, teacher-experience, and pack-validation tests.
- Run `git diff --check` for touched files.

## Task 2: Make routing, catalog loading, and extended evidence gates executable

### Requirements

- Add a deterministic `chatmaker-route` runtime/CLI that accepts structured project intent and returns `hardware`, `web`, `combined`, or `clarify`.
- A combined route must return a blocked/planning state until a communication contract names transport plus at least one request/response or message interaction. It must never promote page rendering to hardware evidence.
- Keep ChatMaker as a thin router: return specialist routes and contract requirements; do not duplicate firmware or page generation.
- Make `catalog_get` load only the requested record path rather than parsing the full catalog. Search may scan summaries, but repeated operations must not reread unchanged YAML unnecessarily.
- Validate every verification entry, including recipe-specific extension gates such as Wi-Fi and HTTP, with the same gate schema and the rule that `verified` requires a date and evidence.
- Document extension gates without making them falsely applicable to every board/component/recipe.

### Verification

- Add behavior tests for hardware, web, ambiguous, and combined-with/without-contract routes.
- Add a test proving exact catalog get does not load unrelated YAML records.
- Add schema/runtime tests for valid and invalid extension gates.
- Run the focused router, catalog, and pack-validation tests plus `git diff --check`.

## Task 3: Implement the beginner creative brief and opt-in advanced ChatWeb playground

### Requirements

- Add an executable creative-brief planner for ChatWeb. A vague brief returns at most two plain-language questions about the missing idea, audience/scene, desired feeling/core message, or primary action. It must not recommend styles before the load-bearing gaps are answered.
- A sufficiently clear brief returns two or three curated directions. Each direction includes feeling, primary interaction, suitable scene, and a meaningful tradeoff.
- Add at least two extra directions per project kind, but expose them only when `advanced` is explicitly true.
- Add an explicit advanced-playground generator/CLI that creates one self-contained local HTML file for comparing the expanded directions. It must not be part of the beginner default.
- Keep generated files free of external CDN dependencies, use at least 44 px touch targets, visible focus, reduced-motion support, and clear simulation labels for hardware concepts.
- Update ChatWeb Skill instructions to call the creative planner and to offer the playground only after the user asks for more.
- Add real Chromium automation for the classroom example, simulated-hardware example, ESP32 AP page, and advanced playground. Assert the primary interaction, phone-width layout/touch target, and zero console errors. The ESP32 page test must preserve the distinction between simulation and real hardware.
- Add the browser suite to CI using an explicit test dependency and browser-install step.

### Verification

- Run focused unit tests and the real browser suite locally.
- Regenerate any checked-in generated example from its single source.
- Run `git diff --check`.

## Task 4: Build and validate the rc5 release candidate

### Requirements

- Bump package/release defaults to `0.1.0rc5` / `0.1.0-rc5`.
- Write bilingual current-version documentation and release notes that include Nano/Uno, official ESP32 preparation/compile-upload, the embedded AP page, executable routing and creative planning, the advanced opt-in playground, WorkBuddy `1.7.0` with 23 tools, and browser automation.
- Keep rc1-rc4 as historical releases. Do not rewrite their historical verification records.
- Update installation instructions so rc5 users can execute all commands contained in the archive, with separate Mind+ and official Arduino CLI prerequisites.
- Strengthen the release test to require the rc5 ESP32 runtime, web embed/planner/playground, router, AP sources, browser tests, and installer assets.
- Build the archive twice and prove byte-identical SHA-256 output.
- Extract into a new temporary directory and validate install/import, doctor, Skill validation, WorkBuddy stdio tool listing, Nano/Uno compile, ESP32 Blink/AP compile, and browser tests from the extracted source.
- Record exact evidence and every still-unverified hardware gate in a new rc5 verification document.

### Verification

- Run the complete unit/browser suite, doctor, Skill validation, release test, deterministic double build, clean-extraction checks, and `git diff --check`.
- Do not mark rc5 published until the Git commit, push, CI, tag, and GitHub prerelease asset states are each independently confirmed.
