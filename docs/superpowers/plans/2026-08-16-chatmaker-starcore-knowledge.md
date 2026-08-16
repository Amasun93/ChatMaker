# Starcore Knowledge Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add IDMC-0001 Starcore v4.2.2 as a governed ChatMaker board with public usage knowledge, representative modules and compiled examples, while keeping manufacturing assets private.

**Architecture:** Register hashes and evidence boundaries for owned local sources, then publish only rewritten board facts, component cards, recipes, and eight passive Knowledge pages. Compilation uses the current Mind+ 1.8 target and records every later hardware gate separately.

**Tech Stack:** YAML/Markdown knowledge contracts, Python validation, Mind+ 1.8 Arduino backend, unittest, deterministic `.cmpack` builder.

## Global Constraints

- Stable board ID is `idmc-0001-starcore-v4-2-2`.
- Board identity is `IDMC-0001 星核板 v4.2.2`.
- Mind+ 1.8 target is `dfrobot:mpython:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none`.
- Mind+ 2.0 historical target is separately recorded as `mindplus:esp32:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none`.
- Never expose local absolute source paths or copy STEP, complete DXF, Gerber, SCH, PCB/production files, raw archives, unlicensed source documents, or high-resolution renders.
- Do not add Star board data, mechanical/CAD pages, or manufacturing dimensions.
- Firmware upload, serial runtime, reboot, sensor readings, network exchange, and physical effects remain `unverified` without hardware.

---

### Task 1: Register owned local sources and publication boundary

**Files:**
- Modify: `knowledge_sources/schemas/source-manifest.schema.yaml`
- Create: `knowledge_sources/manifests/idmc-0001-starcore-v4-2-2.yaml`
- Modify: `tests/test_knowledge_pipeline.py`
- Modify: `scripts/validate_knowledge_publication.py`

**Interfaces:**
- Produces: source ID `source-idmc-0001-starcore-v4-2-2-owned-docs` and eight declared public Knowledge pages.

- [ ] **Step 1: Write failing tests** that accept the new board ID and owned-local hash metadata but reject absolute paths and manufacturing extensions in published content.
- [ ] **Step 2: Compute hashes from the approved local source set** without copying original bytes into the repository or logs.
- [ ] **Step 3: Create a manifest** whose license boundary allows rewritten use guidance only and whose review/approval gates cite the local archive index rather than exposing its path.
- [ ] **Step 4: Run** `python -m unittest tests.test_knowledge_pipeline -v` and publication validation.
- [ ] **Step 5: Commit** `docs: register governed Starcore sources`.

### Task 2: Add the canonical board record and compact index

**Files:**
- Create: `packs/boards/idmc-0001-starcore-v4-2-2.yaml`
- Create: `knowledge/boards/idmc-0001-starcore-v4-2-2.yaml`
- Modify: `runtime/chatmaker/knowledge_semantics.py`
- Modify: catalog, doctor, MCP, schema, and validation tests that enumerate boards

**Interfaces:**
- Produces: fourth canonical board and pack ID `chatmaker-board-idmc-0001-starcore-v4-2-2-knowledge`.

- [ ] **Step 1: Add failing board tests** for exact identity, two distinct toolchain targets, GPIO/I2C facts, input-only pins, startup-sensitive pins, and separate evidence gates.
- [ ] **Step 2: Implement the board record** from source-reviewed facts only. Record the source-file chip-name typo as a note; do not promote unconfirmed CH9102F/QMI8658C claims.
- [ ] **Step 3: Add the eight-section compact index** for the same consumers used by existing boards.
- [ ] **Step 4: Run catalog, doctor, semantic, MCP, and schema tests**; expected board/index counts become 4.
- [ ] **Step 5: Commit** `feat: add Starcore board identity and index`.

### Task 3: Add first-wave owned modules

**Files:**
- Create seven component records under `packs/components/`
- Modify: `tests/test_catalog.py`

**Interfaces:**
- Produces: separate IDs for IDMD-0001 RGB, IDMD-0002 serial MP3, IDMD-0021 OLED 1.3, IDMS-0001 button, IDMS-0003 potentiometer, IDMS-0008 DHT11, and IDMS-0009 ultrasonic.

- [ ] **Step 1: Write catalog tests** proving these owned modules remain distinct from generic parts with similar functions.
- [ ] **Step 2: Author each component card** with ID marking, safe supply/logic boundary, compatible Starcore connection, required library, and source/evidence state.
- [ ] **Step 3: Mark batch-sensitive voltage, echo, and default-pin claims conditional** instead of inventing a universal value.
- [ ] **Step 4: Run schema and catalog tests** and commit `feat: add first Starcore module cards`.

### Task 4: Publish eight rewritten Knowledge pages

**Files:**
- Create: `knowledge_sources/published/boards/idmc-0001-starcore-v4-2-2/*.md`
- Create/modify: Knowledge validation tests for the fourth board

**Interfaces:**
- Produces: `start-here`, `identify-and-safety`, `pins-and-electrical`, `toolchains-and-upload`, `components-and-wiring`, `libraries-and-examples`, `web-and-protocol`, and `troubleshooting`.

- [ ] **Step 1: Write tests** requiring source refs, complete bodies, no local paths, no prohibited extension names, and no mechanical/CAD section.
- [ ] **Step 2: Write beginner-facing pages** in original language, linking canonical IDs rather than duplicating conflicting numeric facts.
- [ ] **Step 3: Explain S/V/G and I2C wiring plainly**, distinguish Mind+ 1.8 from 2.0, and preserve all runtime evidence boundaries.
- [ ] **Step 4: Run Knowledge page and publication tests** and commit `docs: publish Starcore usage knowledge`.

### Task 5: Add and compile representative recipes

**Files:**
- Create: `examples/chatduino/starcore/<recipe>/...`
- Create: corresponding recipes under `packs/recipes/`
- Create: `runtime/chatmaker/hardware/starcore_mindplus.py`
- Create: `tests/hardware/test_starcore_mindplus.py`
- Create: `tests/hardware/test_starcore_examples.py`

**Interfaces:**
- Produces: doctor/compile support plus `starcore-smoke-heartbeat`, `starcore-rgb-pwm`, `starcore-dht11-serial`, `starcore-oled-english`, `starcore-ws2812-strip`, `starcore-ultrasonic-serial`, `starcore-ultrasonic-servo`, `starcore-serial-mp3`, and `starcore-i2c-scan`.

- [ ] **Step 1: Write bridge tests** for Mind+ 1.8 target selection, historical 2.0 separation, absent wired port, UTF-8 JSON, and dependency preflight.
- [ ] **Step 2: Implement doctor and compile operations** by reusing safe subprocess/port patterns from existing bridges.
- [ ] **Step 3: Create minimal examples and recipe records** with explicit wiring and expected effects. Conditional examples remain conditional without hardware.
- [ ] **Step 4: Actually compile every selected example** with the Mind+ 1.8 target, recording return code, Flash/RAM usage, toolchain version, and source hash. Do not upload.
- [ ] **Step 5: Keep upload/serial/physical gates unverified**, run focused tests, and commit `feat: add compiled Starcore examples`.

### Task 6: Build and inspect the Starcore Knowledge pack

**Files:**
- Create: `distribution/packs/chatmaker-board-idmc-0001-starcore-v4-2-2-knowledge-1.0.0.cmpack`
- Modify: pack/release tests

**Interfaces:**
- Produces: a deterministic passive pack containing only `knowledge/index.yaml` and eight `knowledge/sections/*.md` files.

- [ ] **Step 1: Build twice** and assert byte identity and matching SHA-256.
- [ ] **Step 2: Inspect every archive path and manifest field**, proving no manufacturing asset, local path, executable, link, or install hook exists.
- [ ] **Step 3: Install into a temporary state root, read a section, repeat without network, and verify provenance**.
- [ ] **Step 4: Run repository leak scanning and all Starcore-focused tests**.
- [ ] **Step 5: Commit** `build: add governed Starcore Knowledge pack`.

