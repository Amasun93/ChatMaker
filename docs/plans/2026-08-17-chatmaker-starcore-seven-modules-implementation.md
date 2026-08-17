# ChatMaker Starcore Seven-Module Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate seven owned Starcore modules into ChatMaker Knowledge, ChatDuino examples, compile verification, and trustworthy ChatCAD mechanical profiles without any runtime dependency on legacy Skills.

**Architecture:** Keep ChatMaker as the only user entry and retain ChatDuino, ChatWeb, and ChatCAD as separately maintained internal Skills. Migrate approved legacy facts through canonical component/recipe/mechanical records, then make every runtime consumer read only checked-in ChatMaker data and tools.

**Tech Stack:** Python 3.11, YAML/JSON schemas, Markdown Knowledge pages, Arduino C++ through Mind+ 1.8 `arduino-builder`, unittest, deterministic `.cmpack` archives, Ed25519-signed registry metadata.

---

## Global constraints

- Preserve the existing `skills/chatmaker`, `skills/chatduino`, `skills/chatweb`, and `skills/chatcad` source layout.
- User documentation starts at ChatMaker; internal Skills remain independently maintainable and callable by ChatMaker.
- Never import, open, search, or require a legacy Skill at runtime.
- Stable board ID is `idmc-0001-starcore-v4-2-2`.
- Current compile target is `dfrobot:mpython:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none`.
- Keep Mind+ 2.0 as historical knowledge only.
- Do not publish raw STEP, DXF, Gerber, schematic, PCB, source archives, local paths, or other manufacturing source material.
- Upload, serial, reboot, network, display, sound, sensor, actuator, and physical-fit gates remain `unverified` without new hardware evidence.
- Work test-first and commit after each task.

### Task 1: Freeze the single-entry and independence contract

**Files:**
- Modify: `docs/contracts/v1-creative-flow.md`
- Modify: `skills/chatmaker/SKILL.md`
- Modify: `skills/chatduino/SKILL.md`
- Modify: `skills/chatweb/SKILL.md`
- Modify: `skills/chatcad/SKILL.md`
- Delete: `skills/chatduino/agents/openai.yaml`
- Delete: `skills/chatweb/agents/openai.yaml`
- Delete: `skills/chatcad/agents/openai.yaml`
- Modify: `runtime/chatmaker/skills.py`
- Modify: `runtime/chatmaker/installers/workbuddy.py`
- Modify: `runtime/chatmaker/installers/transaction.py` only if the existing transaction cannot atomically migrate and restore the managed MCP key
- Modify: `README.md`
- Modify: `README_EN.md`
- Modify: `RELEASE_NOTES.md`
- Create: `tests/skills/test_chatmaker_entry_and_independence.py`
- Modify: `tests/test_skill_validation.py`
- Modify: `tests/installers/test_host_adapters.py`
- Modify: `tests/installers/test_auto_installer.py`
- Modify: `tests/release/test_release_package.py`
- Modify: `tests/release/test_clean_core_integration.py`

**Step 1: Write the failing contract test**

Require ChatMaker to name all three internal Skills, require each specialist to identify ChatMaker as its parent entry, require only ChatMaker to carry user-facing UI metadata, reject runtime references to known legacy Skill package paths and external Skill roots, and require README installation prompts to start users at ChatMaker. Add WorkBuddy transaction tests that rename the historical MCP key only when its command exactly targets `chatmaker.integrations.mcp`, preserve a genuine unrelated legacy server byte-for-byte, avoid duplicate servers, remain idempotent, restore the original key/value, uninstall back to the before-image, and allow a real legacy plugin to coexist with the new ChatMaker key.

**Step 2: Run the RED test**

Run: `python -m unittest tests.skills.test_chatmaker_entry_and_independence -v`

Expected: FAIL because internal Skills still expose independent user prompts, the historical MCP key remains active, and stale release/Skill assertions do not describe the current four-Skill package.

**Step 3: Implement the smallest documentation contract**

Keep the four existing Skill directories and specialist workflows. Remove only their user-facing UI metadata, allow internal Skills to omit that metadata in validation, clarify parent routing, migrate only the proven ChatMaker MCP entry, and repair current stale release assertions to the existing four Skills, four boards, thirteen components, sixteen recipes, registry sequence 3, current commands, and packaged-link contract before feature counts change. Bring Clean Core to a green current baseline here, before adding any module records.

**Step 4: Run focused validation**

Run: `python -m unittest tests.skills.test_chatmaker_entry_and_independence tests.test_skill_validation tests.test_route tests.installers.test_host_adapters tests.installers.test_auto_installer tests.release.test_release_package tests.release.test_clean_core_integration -v`

Expected: PASS.

**Step 5: Commit**

Commit: `docs: freeze ChatMaker single-entry architecture`

### Task 2: Govern the seven-module migration sources

**Files:**
- Modify: `knowledge_sources/manifests/idmc-0001-starcore-v4-2-2.yaml`
- Modify: `packs/boards/idmc-0001-starcore-v4-2-2.yaml`
- Modify: `packs/schemas/board.schema.yaml`
- Modify: `knowledge_sources/schemas/source-manifest.schema.yaml` only if the existing schema cannot express module-level approvals
- Modify: `scripts/validate_knowledge_publication.py`
- Modify: `tests/test_knowledge_pipeline.py`
- Modify: `tests/test_pack_validation.py`
- Create: `docs/verification/2026-08-17-starcore-seven-module-source-audit.md`

**Step 1: Write failing governance tests**

Require all seven hardware IDs, approved rewritten-use scope, source hashes or source IDs, public/private boundaries, and explicit rejection of absolute paths and manufacturing source extensions in published files. Strengthen canonical validation so every constraint-referenced pin exists, P15/P16 UART roles have sources, and 5V is represented as an explicit power rail/connector rather than a GPIO. Keep the MP3 recipe blocked if that evidence is insufficient.

**Step 2: Run the RED test**

Run: `python -m unittest tests.test_knowledge_pipeline tests.test_pack_validation -v`

Expected: FAIL because the current manifest does not enumerate the complete seven-module migration contract.

**Step 3: Audit and record approved facts**

Read the approved legacy source tree only during development. Record public facts and evidence levels without copying raw source bytes or local paths into the repository. Add P16 and a 5V rail/connector to the canonical board only when the approved source confirms their exact meaning; otherwise leave the MP3 power/recipe blocked rather than inventing a board pin.

**Step 4: Run publication validation**

Run: `python scripts/validate_knowledge_publication.py && python -m unittest tests.test_knowledge_pipeline tests.test_pack_validation -v`

Expected: exit 0 with no path or manufacturing-source leak.

**Step 5: Commit**

Commit: `docs: govern Starcore module migration sources`

### Task 3: Add seven distinct canonical component cards

**Files:**
- Create: `packs/components/idmd-0001-starcore-rgb-light.yaml`
- Create: `packs/components/idmd-0002-starcore-serial-mp3.yaml`
- Create: `packs/components/idmd-0021-starcore-oled-1-3.yaml`
- Create: `packs/components/idms-0001-starcore-button.yaml`
- Create: `packs/components/idms-0003-starcore-potentiometer.yaml`
- Create: `packs/components/idms-0008-starcore-dht11.yaml`
- Create: `packs/components/idms-0009-starcore-ultrasonic.yaml`
- Modify: `tests/test_catalog.py`
- Modify: `tests/test_knowledge_validation.py`
- Modify: `tests/release/test_release_package.py`
- Modify: `tests/release/test_clean_core_integration.py`

**Step 1: Write failing catalog tests**

Assert exact IDs, Chinese aliases, Starcore-only `supported_boards`, required evidence gates, explicit supply/logic boundaries, Mind+ headers/extensions, and separation from generic RGB, OLED, button, potentiometer, DHT11, and HC-SR04 records. Explicitly prove that IDMD-0001 is not WS2812, IDMS-0001 is not the I2C RGB button, and IDMS-0009 is not the `sen0304` I2C ultrasonic module.

Also update `open_board` expectations and freeze the post-component-card total at twenty components. Treat legacy compile reports as separate evidence keys rather than current `code_compiled` proof.

**Step 2: Run the RED test**

Run: `python -m unittest tests.test_catalog tests.test_knowledge_validation tests.release.test_release_package tests.release.test_clean_core_integration -v`

Expected: FAIL with missing owned component IDs.

**Step 3: Create the cards**

Use source-reviewed facts only. Mark batch-sensitive voltage, address, echo level, pin, and physical behavior claims conditional or unverified.

Compilation evidence remains recipe-owned. Component cards may reference an evidence ID in `code_compiled`, while `historical_lead` remains outside the current gate.

**Step 4: Run schema and catalog tests**

Update the green release snapshot to four boards, twenty components, and sixteen recipes, then run: `python -m unittest tests.test_catalog tests.test_knowledge_validation tests.release.test_release_package tests.release.test_clean_core_integration -v`

Expected: PASS.

**Step 5: Commit**

Commit: `feat: add seven owned Starcore components`

### Task 4: Add seven beginner-facing recipes and examples

**Files:**
- Create: `packs/recipes/starcore-idmd-0001-rgb-pwm.yaml`
- Create: `packs/recipes/starcore-idmd-0002-serial-mp3.yaml`
- Create: `packs/recipes/starcore-idmd-0021-oled-message.yaml`
- Create: `packs/recipes/starcore-idms-0001-button-input.yaml`
- Create: `packs/recipes/starcore-idms-0003-potentiometer-read.yaml`
- Create: `packs/recipes/starcore-idms-0008-dht11-serial.yaml`
- Create: `packs/recipes/starcore-idms-0009-ultrasonic-distance.yaml`
- Create: matching `examples/chatduino/starcore/<recipe>/<recipe>.ino` files
- Create: `tests/hardware/test_starcore_owned_examples.py`
- Modify: `tests/skills/test_chatduino_experience.py`
- Modify: `tests/release/test_release_package.py`
- Modify: `tests/release/test_clean_core_integration.py`

**Step 1: Write failing recipe and output tests**

Require each recipe to reference the exact board and owned component ID, point to a complete source file, include safe wiring, and expose simple disconnected-power text plus complete C++ through the ChatDuino contract. Determine whether the existing Starcore OLED and ultrasonic examples used owned or generic hardware; move their example/evidence ownership to exactly one canonical card and forbid duplicate proof.

Freeze the post-recipe total at twenty-three recipes only after all seven recipe and source files exist.

Hard gate: do not create the MP3 recipe or source unless Task 2 has source-confirmed P16 UART meaning and a valid 5V power-rail/connector expression. If either remains unresolved, report the evidence blocker and stop Tasks 4-6 rather than inventing values to satisfy the seven-item target.

**Step 2: Run the RED test**

Run: `python -m unittest tests.hardware.test_starcore_owned_examples tests.skills.test_chatduino_experience tests.release.test_release_package tests.release.test_clean_core_integration -v`

Expected: FAIL because recipes and examples are missing.

**Step 3: Implement minimal complete examples**

Use verified Mind+ 1.8 APIs and extension headers. Keep adjustable constants at the top, safe startup states, serial diagnostics, and non-blocking timing where appropriate. OLED uses the `MPython.h` global `display`; MP3 uses `DFRobot_SerialMp3.h`; DHT11 uses `DFRobot_DHT.h` with 2500 ms alternating getter calls; ultrasonic uses `DFRobot_URM10.h` with `P_H/P_O` and treats zero as timeout/failure.

**Step 4: Run static and catalog checks**

Update the green release snapshot to four boards, twenty components, and twenty-three recipes, then run: `python -m unittest tests.hardware.test_starcore_owned_examples tests.test_catalog tests.skills.test_chatduino_experience tests.release.test_release_package tests.release.test_clean_core_integration -v`

Expected: PASS before real compilation.

**Step 5: Commit**

Commit: `feat: add Starcore owned-module recipes`

### Task 5: Compile every owned-module example

**Files:**
- Modify: `runtime/chatmaker/hardware/starcore.py` only if dependency preflight or structured diagnostics need a minimal extension
- Modify: `tests/hardware/test_starcore.py`
- Modify: `tests/hardware/test_starcore_owned_examples.py`
- Create: `docs/verification/2026-08-17-starcore-seven-module-compilation.md`
- Modify: the seven component and recipe records from Tasks 3-4 to record verified compilation evidence

**Step 1: Write failing compile-contract tests**

Assert current/historical FQBN separation, required extension/header discovery, UTF-8 paths, no wired-port requirement for compile, and structured failures for missing dependencies.

**Step 2: Run the RED test**

Run: `python -m unittest tests.hardware.test_starcore tests.hardware.test_starcore_owned_examples -v`

Expected: FAIL only for the newly required dependency/evidence behavior.

**Step 3: Implement the smallest bridge changes**

Do not copy the legacy bridge wholesale. Reuse the existing ChatMaker Starcore adapter and add only missing deterministic behavior.

**Step 4: Perform real compilation**

Compile all seven checked-in examples through the current Mind+ 1.8 target. Each recipe/example owns one evidence record containing source hash, target, exit code, Flash/RAM output, and artifact paths; the component gate only references that evidence ID. Do not promote legacy boolean/report-only compile claims; preserve them only as historical leads. Do not upload.

**Step 5: Run focused regression and commit**

Run: `python -m unittest discover -s tests/hardware -p 'test_starcore*.py' -v && python -m unittest tests.test_catalog tests.test_pack_validation tests.test_knowledge_validation -v`

Expected: PASS; upload and physical gates remain unverified.

Commit: `test: verify seven Starcore module examples`

### Task 6: Publish the seven modules in Starcore Knowledge

**Files:**
- Modify: `knowledge_sources/published/boards/idmc-0001-starcore-v4-2-2/components-and-wiring.md`
- Modify: `knowledge_sources/published/boards/idmc-0001-starcore-v4-2-2/libraries-and-examples.md`
- Modify: `knowledge_sources/published/boards/idmc-0001-starcore-v4-2-2/troubleshooting.md`
- Modify: `tests/hardware/test_common_module_knowledge.py`
- Modify: `tests/test_knowledge_contracts.py`
- Modify: `tests/release/test_release_package.py`
- Modify: `tests/release/test_clean_core_integration.py`
- Create: `distribution/packs/chatmaker-board-idmc-0001-starcore-v4-2-2-knowledge-1.2.0.cmpack`
- Modify: `distribution/registry/registry.json`
- Modify: `distribution/registry/registry.sig.json` only through the approved external-key signing command

**Step 1: Write failing Knowledge tests**

Require all seven IDs in the correct pages, canonical links instead of duplicated numeric facts, beginner explanations, library/extension mapping, and no local/manufacturing leaks.

Require the source-confirmed MP3 P16/5V gate from Task 2; if it is not satisfied, do not publish a pack claiming seven complete modules.

**Step 2: Run the RED test**

Run: `python -m unittest tests.test_knowledge_contracts tests.hardware.test_common_module_knowledge -v`

Expected: FAIL because the pages and pack do not contain the seven-module release.

**Step 3: Rewrite the pages and build the pack twice**

Run `scripts/build_pack.py` with the next Starcore pack version. Assert byte-identical archives and matching SHA-256.

**Step 4: Commit the deterministic pack**

Commit: `build: add Starcore module knowledge pack`

Capture this commit's exact 40-character SHA. Only after it exists, update the registry URL/length/hash, increment the current sequence, and sign the exact registry bytes with the approved repository-external signing key without reading or printing its private material.

**Step 5: Sign, smoke test, and commit the registry**

Verify first download, cache reuse, offline section read, and rollback behavior in temporary state roots.

Update registry/pack snapshot assertions at each of the two commit gates, then run: `python -m unittest tests.test_knowledge_contracts tests.test_pack_validation tests.installers.test_pack_artifact tests.installers.test_pack_manager tests.release.test_release_package tests.release.test_clean_core_integration -v`

Expected: PASS.

Commit: `build: publish Starcore module registry`

### Task 7: Add trustworthy component mechanical profiles to ChatCAD

**Files:**
- Create: `knowledge/mechanical/schemas/component-profile.schema.json`
- Create: `knowledge/mechanical/components/idmd-0001-starcore-rgb-light.json`
- Create: `knowledge/mechanical/components/idmd-0002-starcore-serial-mp3.json`
- Create: `knowledge/mechanical/components/idmd-0021-starcore-oled-1-3.json`
- Create: `knowledge/mechanical/components/idms-0001-starcore-button.json`
- Create: `knowledge/mechanical/components/idms-0003-starcore-potentiometer.json`
- Create: `knowledge/mechanical/components/idms-0008-starcore-dht11.json`
- Create: `knowledge/mechanical/components/idms-0009-starcore-ultrasonic.json`
- Modify: `knowledge/mechanical/source-registry.json`
- Modify: `runtime/chatmaker/cad/profiles.py`
- Modify: `runtime/chatmaker/cad/generator.py`
- Modify: `runtime/chatmaker/doctor.py`
- Modify: `runtime/chatmaker/integrations/workbuddy_mcp.py`
- Modify: `tests/test_cad.py`
- Create: `tests/test_starcore_component_mechanics.py`
- Modify: `tests/integrations/test_workbuddy_mcp.py`
- Modify: `tests/release/test_clean_core_integration.py`

**Step 1: Write failing mechanical tests**

Require MP3, OLED, DHT11, and ultrasonic panel features plus only source-confirmed mounting geometry for RGB, button, and potentiometer. Require record-level `source_ids` and verification plus a per-feature evidence status; reject guessed heights or interface centers. If a geometry fact is not source-confirmed, the record must explicitly mark that feature `not_available` or `unverified` and omit numeric geometry rather than filling a value to satisfy the schema. Keep all seven `physical_fit=unverified` until printed or fabricated coupons are checked against real modules. Freeze the runtime action as `component-profile` with request `{"action":"component-profile","component_id":"<id>"}` and the WorkBuddy tool as `cad_component_profile_get`.

**Step 2: Run the RED test**

Run: `python -m unittest tests.test_cad tests.test_starcore_component_mechanics tests.integrations.test_workbuddy_mcp tests.release.test_clean_core_integration -v`

Expected: FAIL because component profiles and lookup are missing.

**Step 3: Implement component-profile loading**

Define and validate the component-profile contract first, then extend the existing profile layer without changing board-profile behavior. Keep board and component IDs explicit and validate positive dimensions, finite coordinates, evidence fields, and safe paths. Add doctor validation and ensure the Core artifact contains the schema and records.

**Step 4: Run CAD regression**

Update the exact WorkBuddy tool set/version and Clean Core tool count in the same commit, then run: `python -m unittest tests.test_cad tests.test_starcore_component_mechanics tests.integrations.test_workbuddy_mcp tests.release.test_clean_core_integration -v`

Expected: PASS; generated-file status is separate from physical fit.

**Step 5: Commit**

Commit: `feat: add Starcore component mechanics`

### Task 8: Prove clean independence and finish the release

**Files:**
- Modify: `tests/release/test_clean_core_integration.py`
- Modify: `tests/release/test_release_package.py`
- Modify: `tests/installers/test_auto_installer.py`
- Modify: `docs/contributing/pack-format.md`
- Modify: `README.md`
- Modify: `docs/verification/v1.0-acceptance.md`
- Create: `docs/verification/2026-08-17-starcore-seven-module-release.md`

**Step 1: Write failing clean-environment tests**

Build a clean Core artifact, provide a HOME without legacy Nano/Starcore/UNIHIKER Skills, install ChatMaker, and verify ChatMaker routing, all internal Skill bundles, seven component lookups, example discovery, Starcore doctor, Knowledge reads, and component mechanical-profile reads. Every earlier snapshot-changing task must already have kept this suite green; Task 8 adds the final no-legacy-Skill independence scenarios and verifies every packaged README link resolves inside the Core artifact.

**Step 2: Run the RED test**

Run: `python -m unittest tests.release.test_clean_core_integration tests.release.test_release_package tests.installers.test_auto_installer -v`

Expected: FAIL until release paths and counts include the seven-module release.

**Step 3: Update release/docs without changing architecture**

Document ChatMaker as the user entry, internal Skills as maintained specialists, and legacy Skills as migration-only sources. Keep all hardware gates honest.

**Step 4: Run focused and full verification**

Run:

```text
python -m unittest tests.test_catalog tests.hardware.test_starcore_owned_examples tests.test_starcore_component_mechanics tests.skills.test_chatmaker_entry_and_independence -v
python -m unittest discover -s tests -v
python runtime/doctor.py
git diff --check
```

Expected: all tests pass except explicitly documented platform/privilege skips; doctor succeeds; diff check is clean.

**Step 5: Refresh installed Skills and verify bytes**

Run `chatmaker-install auto` and `chatmaker-install doctor`. Compare installed `chatmaker`, `chatduino`, `chatweb`, and `chatcad` bundles byte-for-byte with the release source. Confirm both Codex and WorkBuddy hosts are healthy.

**Step 6: Commit**

Commit: `docs: finish Starcore seven-module migration`

### Task 9: Independent review, merge, and push

**Files:**
- Review the full branch diff from `main` to the feature head.
- Update review reports under the task's local review directory.

**Step 1: Independent specification review**

Verify every acceptance item in the design and every global constraint in this plan. Treat missing runtime independence, unsafe electrical claims, private-source leakage, or false verification promotion as blocking.

**Step 2: Independent quality/security review**

Review parsing, path handling, release packaging, deterministic pack output, signature trust, registry sequence, and mechanical-data validation.

**Step 3: Fix with RED-GREEN loops**

For each Critical or Important finding, add a reproducing test, observe RED, implement the minimum fix, rerun focused and full tests, then request scoped rereview.

**Step 4: Merge and push**

After a clean rereview and fresh full verification, fast-forward `main`, push without force, and verify local `main`, `origin/main`, and GitHub report the same commit SHA.

**Step 5: Complete the long goal**

Only mark the goal complete after code, packs, installation refresh, review, merge, and push are all evidenced.
