# Domestic preparation and classroom startup

Approved scope: user approved steps 1 and 2 of the 2026-11-12 feedback assessment, development in D:/Projects/ChatMaker, and GitHub synchronization. Continue the existing branch, including the previously approved S3 changes. No physical flash is needed to implement or verify this upgrade.

## Contract

- A Windows x64 classroom entry prepares its own pinned CLI, core, required tools and libraries without Mind+/Arduino IDE or global configuration changes.
- Classic ESP32 and Waveshare S3 use the same bounded download/installation primitives. Select only dependencies needed by supported compile/upload profiles; never delete unrelated Arduino installations.
- Exact artifact identity across domestic-first fallback sources, restartable downloads, explicit stages/progress, unchanged final JSON protocol, read-only preview/doctor, cache reuse.
- CLI format compatibility, simple arguments and file/stdin requests, source/installed/runtime provenance and version mismatch detection.
- WorkBuddy instructions select the released Git revision and explicit D: runtime, and distinguish software checks from physical observations.

## Tasks

### Task 1: Compatibility and provenance
Fix modern core-list parsing with captured-shape regression tests. Add common argument/provenance utilities and a board-aware action entry with diagnostics/preview/compile/run. Keep strict legacy adapter behavior for explicitly supplied external candidates. Tests: hardware compatibility and entry tests.

### Task 2: Reliable shared downloads
Extend the existing downloader, preserving injectable fetchers and cache contracts. Resume verified-identity partial files, bound retries and source switching, validate ranges/final size/hash, enforce redirect policy before network access, and emit progress to a separate channel. Tests: local HTTP server interrupted/resumed/ignored-range/wrong-content/source-policy cases plus existing installer suite.

### Task 3: Selective managed toolchains
Build a checked-in lock from official ESP32 3.3.11 Windows archive metadata, Arduino dependencies and CLI 1.3.1. Install selected archives atomically into isolated profiles, with offline indexes, complete manifests, verified cache reuse and preparation preview. Reuse vendor extraction for S3. Test core/SDK omissions, interrupted installation, wrong hash/config, and managed compile commands. Validate actual classic ESP32 and S3 V1/V2 compilations in isolated environments. Add Nova only as an explicit known-chip/4MB profile; never infer board identity from CH340.

### Task 4: Integration and classroom handoff
Wire preparation, stages, error remedies and exact source identity through host instructions and adapters. Prepare a version-checked WorkBuddy script/instructions covering fresh install, cache, interruption and physical tasks. Run full Python/browser/doctor/skill checks and real compiler validation; capture sizes and limits without claiming physical validation.

### Task 5: Review and GitHub synchronization
Request one independent whole-change review, fix important findings with regressions, commit, fast-forward the default branch only if remote history permits, push and read back the commit/ref. Give the user the exact revision and WorkBuddy document.

## Shared interfaces and review focus

Downloader progress must never corrupt final stdout JSON. Preparation cannot trigger implicit CLI network updates or silently ignore domestic-only on redirects. A receipt must cover every compiled dependency and relevant configuration, not merely executable presence. Profile selection must not relax upload identity/port safeguards. Cached archives and installed environments have separate validity. Windows paths, atomic replacement, concurrent preparation, shell quoting and no-write diagnostics need deliberate review.

## Validation

Use the repository Python 3.11 runtime. Keep Windows test temp paths short and outside Git worktrees. Run `python -m unittest discover -s tests -v`, `npm run test:browser`, `python runtime/doctor.py`, and `python scripts/validate_skills.py` with captured logs. Real compilation runs use explicit isolated configs; never flash attached hardware during development verification.
