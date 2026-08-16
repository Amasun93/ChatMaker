# ChatMaker Auto Installer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide one capability-driven `chatmaker-install` entry point that installs, verifies, restores, and removes ChatMaker safely on Windows and macOS.

**Architecture:** A read-only capability probe feeds internal host adapters. The orchestrator turns adapter proposals into a journaled, locked transaction so repeat installs are idempotent and failures preserve user Skills and MCP settings.

**Tech Stack:** Python 3.11 standard library plus existing ChatMaker dependencies, unittest, GitHub Actions Windows/macOS runners.

## Global Constraints

- User flow must not require choosing Codex, WorkBuddy, or a fixed AI host.
- Codex and WorkBuddy remain internal adapters; explicit directories are supported for other hosts.
- `auto --dry-run` is read-only.
- User-scoped reversible actions may run automatically; OS elevation and driver confirmation become clear next actions.
- Do not preinstall every board knowledge pack.
- Current hardware environment remains Mind+ compatible; independent no-Mind+ toolchains are out of scope.
- Repeat install, doctor, restore, and uninstall operations must be safe and idempotent.

---

### Task 1: Add the capability report

**Files:**
- Create: `runtime/chatmaker/installers/capabilities.py`
- Create: `tests/installers/test_capabilities.py`

**Interfaces:**
- Produces: `probe_environment(*, home: Path | None = None, environ: Mapping[str, str] | None = None) -> CapabilityReport`.
- `CapabilityReport.to_dict()` returns OS, CPU, Python, terminal, browser, serial, Mind+, Arduino CLI, candidate Skill roots, and MCP configs.

- [ ] **Step 1: Write table-driven tests** for Windows, macOS, no serial device, missing tools, Unicode HOME, explicit paths, and unreadable candidates.
- [ ] **Step 2: Run** `python -m unittest tests.installers.test_capabilities -v` and confirm import failure.
- [ ] **Step 3: Implement bounded detection** using `platform`, `sys`, `shutil.which`, explicit known paths, and existing Mind+/serial helpers. Do not scan entire disks.
- [ ] **Step 4: Verify no-device states are successful capabilities with `available=false`**, not installer failures.
- [ ] **Step 5: Commit** `feat: add cross-platform capability probe`.

### Task 2: Define host adapters and generic MCP entry

**Files:**
- Create: `runtime/chatmaker/installers/hosts/base.py`
- Create: `runtime/chatmaker/installers/hosts/codex.py`
- Create: `runtime/chatmaker/installers/hosts/workbuddy.py`
- Create: `runtime/chatmaker/installers/hosts/explicit.py`
- Create: `runtime/chatmaker/integrations/mcp.py`
- Create: `tests/installers/test_host_adapters.py`
- Modify: `runtime/chatmaker/integrations/workbuddy_mcp.py` only until the generic module fully replaces it

**Interfaces:**
- Produces: `HostAdapter.detect(report)`, `HostAdapter.plan(context)`, and `HostAdapter.verify(context)`.
- Generic MCP entry is `python -m chatmaker.integrations.mcp`.

- [ ] **Step 1: Write tests** for explicit path precedence, high-confidence Codex/WorkBuddy detection, multiple detected hosts, and no recognized host.
- [ ] **Step 2: Verify tests fail**, then implement adapters around existing logic.
- [ ] **Step 3: Ensure a no-host result leaves Core/CLI ready with `ready_with_limits`** and does not write guessed paths.
- [ ] **Step 4: Verify WorkBuddy plans preserve unrelated MCP entries and use generic MCP module execution**.
- [ ] **Step 5: Commit** `refactor: hide host differences behind adapters`.

### Task 3: Add a journaled install transaction

**Files:**
- Create: `runtime/chatmaker/installers/transaction.py`
- Create: `tests/installers/test_install_transaction.py`
- Modify: `runtime/chatmaker/installers/skill_bundle.py`
- Reuse: `runtime/chatmaker/installers/file_lock.py`

**Interfaces:**
- Produces: `InstallTransaction.apply(changes) -> TransactionResult`, `restore(transaction_id)`, and `uninstall()`.
- State lives under `~/.chatmaker/state`, `transactions`, `backups`, and `locks/install.lock`.

- [ ] **Step 1: Write failure-injection tests** for staging, Skill activation, MCP replacement, journal replacement, and verification.
- [ ] **Step 2: Add idempotency tests** proving the second identical install returns `already_current` without new backup or changed hash.
- [ ] **Step 3: Implement locked staging, per-change before-images, atomic journal writes, compensation rollback, and managed-content hashes**.
- [ ] **Step 4: Change normal WorkBuddy uninstall** to remove only ChatMaker's managed MCP entry while preserving later user additions; keep full backups for disaster restore.
- [ ] **Step 5: Run installer regression tests** and commit `feat: make installation transactional and idempotent`.

### Task 4: Implement the universal CLI

**Files:**
- Create: `runtime/chatmaker/installers/auto.py`
- Create: `tests/installers/test_auto_installer.py`
- Modify: `pyproject.toml`
- Modify: `docs/installation.md`

**Interfaces:**
- Produces CLI commands: `chatmaker-install auto`, `auto --dry-run`, `doctor`, `restore`, and `uninstall`.
- JSON result includes `success`, `status`, `environment`, `hosts`, `changes`, `unchanged`, `next_actions`, and `transaction_id`.

- [ ] **Step 1: Write CLI tests** for dry-run, new install, repeated install, partial host support, doctor, restore, uninstall, and JSON output.
- [ ] **Step 2: Verify failures**, then implement orchestration without duplicating adapter or transaction logic.
- [ ] **Step 3: Keep old host-specific modules internal** and remove their user-facing script entries from `pyproject.toml`.
- [ ] **Step 4: Rewrite installation docs around one command** and capability-based outcomes.
- [ ] **Step 5: Run focused tests** and commit `feat: add universal ChatMaker installer`.

### Task 5: Add the standard-library bootstrap

**Files:**
- Create: `scripts/bootstrap.py`
- Create: `tests/installers/test_bootstrap.py`
- Modify: `scripts/build_release.py`
- Modify: `tests/release/test_release_package.py`

**Interfaces:**
- Produces: a bootstrap that installs a versioned Core under `~/.chatmaker/versions/<version>/venv` and then invokes `chatmaker-install auto`.

- [ ] **Step 1: Write tests** using a local Core archive, temporary HOME, no editable install, path with spaces/Chinese, and a second idempotent run.
- [ ] **Step 2: Implement with Python standard library only**, verify archive checksum, create venv, install the local Core, and atomically update the active-version launcher.
- [ ] **Step 3: Ensure bootstrap never downloads drivers, Mind+, Arduino cores, browsers, or board packs**.
- [ ] **Step 4: Add bootstrap to the deterministic Core release and clean-Core smoke test**.
- [ ] **Step 5: Commit** `feat: bootstrap ChatMaker Core from one script`.

### Task 6: Prove Windows and real macOS behavior

**Files:**
- Modify: `.github/workflows/ci.yml`
- Create: `tests/release/test_auto_install_smoke.py`
- Create: `docs/verification/2026-08-16-chatmaker-auto-installer.md`

**Interfaces:**
- Produces: Windows and `macos-14` matrix evidence for the same clean-user workflow.

- [ ] **Step 1: Add matrix tests** that build/extract Core, create a clean venv/HOME, run dry-run, install twice, doctor, Knowledge read, add an unrelated MCP, uninstall, and verify preservation.
- [ ] **Step 2: Assert the report records real `platform.system()` and `platform.machine()`** so macOS is not mocked.
- [ ] **Step 3: Run the Windows smoke locally**, then push the feature branch and inspect GitHub Actions for Windows and macOS success.
- [ ] **Step 4: Record exact run URL, commit, OS values, and limitations**; absence of board/Mind+ remains a nonfatal capability result.
- [ ] **Step 5: Commit** `test: verify universal installer on Windows and macOS`.

