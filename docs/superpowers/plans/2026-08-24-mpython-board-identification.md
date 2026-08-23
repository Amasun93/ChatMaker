# mPython Board Identification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add classic mPython V2.x and mPython 3.0 knowledge while giving ChatMaker a beginner-friendly, evidence-graded board identification flow that preserves Starcore identity and safely restores firmware after an allowed temporary probe.

**Architecture:** Canonical board and Knowledge records remain the source of hardware facts. A new hardware identification module separates pure evidence classification from side-effecting discovery and temporary-probe execution. The probe workflow is transactional: backup, hash verification, probe, restore in `finally`, restore verification, then classification.

**Tech Stack:** Python 3.11, PyYAML, pyserial, Mind+/esptool command adapters, Markdown/YAML Knowledge packs, pytest.

**Spec:** `docs/design/2026-08-24-mpython-board-identification.md`

## Global Constraints

- Keep `mpython-classic-v2x`, `mpython-v3`, and `idmc-0001-starcore-v4-2-2` as independent board identities.
- Never confirm a board from a USB-UART chip, ESP family, or one I2C address alone.
- Temporary firmware requires one eligible wired port and a verified full-Flash backup before any write.
- Always attempt restore after a probe write; do not return `confirmed` when restore verification fails.
- Present beginner guidance before raw technical detail.
- Keep compile, write, restore, runtime, sensor and physical evidence separate.
- Do not modify shared installer, upgrade, uninstall, recovery or registry transaction infrastructure.

---

### Task 1: Add the two mPython board knowledge sets

**Files:**
- Create: `packs/boards/mpython-classic-v2x.yaml`
- Create: `packs/boards/mpython-v3.yaml`
- Create: `knowledge/boards/mpython-classic-v2x.yaml`
- Create: `knowledge/boards/mpython-v3.yaml`
- Create: `knowledge_sources/manifests/mpython-classic-v2x.yaml`
- Create: `knowledge_sources/manifests/mpython-v3.yaml`
- Create: `knowledge_sources/published/boards/mpython-classic-v2x/*.md`
- Create: `knowledge_sources/published/boards/mpython-v3/*.md`
- Test: `tests/hardware/test_mpython_boards.py`
- Test: `tests/test_catalog.py`

**Interfaces:**
- Produces: canonical IDs `mpython-classic-v2x` and `mpython-v3`, each with the standard eight Knowledge sections.

- [ ] Write failing tests requiring separate MCU, display, sensor, pin, API, toolchain and evidence facts for both boards.
- [ ] Write a failing catalog regression proving `掌控板` returns real mPython boards ahead of Starcore compatibility mentions.
- [ ] Add source manifests using official CC0 documentation facts and link software/hardware licenses without copying unclear Mind+ packages.
- [ ] Add canonical board records, compact indexes and eight concise beginner-facing pages per board.
- [ ] Run `python -m pytest tests/hardware/test_mpython_boards.py tests/test_catalog.py tests/test_knowledge_validation.py -q`.

### Task 2: Add pure evidence classification and beginner guidance

**Files:**
- Create: `runtime/chatmaker/hardware/board_identification.py`
- Create: `tests/hardware/test_board_identification.py`
- Modify: `knowledge_sources/published/boards/idmc-0001-starcore-v4-2-2/identify-and-safety.md`
- Modify: `knowledge_sources/published/boards/idmc-0001-starcore-v4-2-2/toolchains-and-upload.md`

**Interfaces:**
- Produces: `classify_evidence(evidence: BoardEvidence) -> IdentificationResult` and `beginner_next_step(result) -> str`.
- Consumes: normalized USB, chip, firmware-marker and probe evidence without performing I/O.

- [ ] Write failing tests for exact Starcore markers, ESP32-S3 mPython 3.0 candidates, classic sensor revisions, overlapping Starcore/classic evidence and photo fallback.
- [ ] Implement minimal immutable evidence/result types and a classifier that returns confirmed, probable, ambiguous or unavailable.
- [ ] Add simple Chinese next-step messages that point to likely silk-screen locations and then request front/back photos.
- [ ] Update Starcore Wiki to explain automatic identity evidence and prohibit mPython compatibility from proving physical identity.
- [ ] Run `python -m pytest tests/hardware/test_board_identification.py tests/hardware/test_starcore_complete_board_knowledge.py -q`.

### Task 3: Add the guarded temporary-probe workflow

**Files:**
- Create: `runtime/chatmaker/hardware/temporary_probe.py`
- Create: `tests/hardware/test_temporary_probe.py`
- Create: `examples/chatduino/board-identification/esp32-mpython-probe/esp32-mpython-probe.ino`

**Interfaces:**
- Produces: `run_temporary_probe(request, adapter) -> ProbeWorkflowResult`.
- Adapter operations: `inspect`, `backup`, `verify_backup`, `write_probe`, `read_report`, `restore`, and `verify_restore`.

- [ ] Write failing state-machine tests proving no write before backup verification, restore after probe/read failure, preserved backup after restore failure, and no confirmed identity when restore is unverified.
- [ ] Implement the minimal adapter-neutral transaction state machine and privacy-safe result object.
- [ ] Add the classic ESP32 probe source with a versioned serial JSON marker; use only source-reviewed I2C signatures and report unknown fields instead of guessing.
- [ ] Add a real Mind+ adapter only for toolchains currently discovered on the machine; return `probe-toolchain-unavailable` for mPython 3.0 until its package is installed.
- [ ] Run `python -m pytest tests/hardware/test_temporary_probe.py -q` and compile the classic probe without uploading.

### Task 4: Expose one identification entry and update Skill routing

**Files:**
- Modify: `runtime/chatmaker/integrations/workbuddy_mcp.py`
- Modify: `pyproject.toml`
- Modify: `skills/chatmaker/SKILL.md`
- Modify: `skills/chatduino/SKILL.md`
- Test: `tests/integrations/test_workbuddy_mcp.py`
- Test: `tests/skills/test_chatduino_experience.py`

**Interfaces:**
- Produces: CLI `chatmaker-board-identify` and WorkBuddy tool `board_identify` with `port` and `allow_temporary_firmware` inputs.

- [ ] Write failing integration tests for tool visibility, no-hardware guidance, ambiguity/photo fallback and temporary-probe consent propagation.
- [ ] Add CLI/MCP routing while keeping raw evidence in structured output and beginner guidance first.
- [ ] Update ChatMaker/ChatDuino routing to identify a connected board before loading exact-board Knowledge.
- [ ] Run focused integration, Skill, catalog, Knowledge and hardware tests once.
- [ ] Review the spec checklist, inspect `git diff`, and record hardware-only checks as unverified rather than claiming physical completion.
