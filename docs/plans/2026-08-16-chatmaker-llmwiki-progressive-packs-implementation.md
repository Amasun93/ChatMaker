# ChatMaker LLMWiki and Progressive Packs Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Deliver a board-centered shared LLMWiki whose detailed official board pages install automatically on first use from a signed GitHub registry, while preserving ChatMaker's canonical catalog, three current Skills, and evidence boundaries.

**Architecture:** Canonical board/component/recipe YAML remains in the core. Compact per-board manifests map consumer topics to optional read-only knowledge-pack IDs; detailed Markdown lives only in deterministic signed `.cmpack` artifacts. A layered reader silently ensures the missing official pack, then reads one complete section from an immutable active version.

**Tech Stack:** Python 3.11, YAML/JSON Schema, Markdown with YAML frontmatter, `cryptography` Ed25519, ZIP/SHA-256, unittest, Playwright, GitHub raw content.

---

## Global Constraints

- Preserve exact current board/component/recipe IDs, built-in counts 3/12/14, canonical verification objects, and legacy `catalog search/get` response shapes.
- Optional knowledge packs may contain only LLMWiki manifests/pages and must not contain canonical board/component/recipe records.
- Keep environment, source, compile, upload, serial/browser, network, power-cycle, mechanical, and physical-effect evidence separate.
- Do not add a ChatCAD Skill, route, CLI, MCP tool, geometry generator, DXF, STL, or 3D implementation.
- Silent installs are limited to signed, allowlisted, passive official `knowledge` packs in user-owned directories.
- Never silently install drivers, toolchains, Arduino cores, Mind+, Node, browsers, edit PATH, request admin elevation, or mutate WorkBuddy MCP configuration through the pack manager.
- Preserve explicit local overrides and label provenance. Reject or quarantine drift in immutable official versions.
- Use TDD, atomic state writes, deterministic archives, explicit compatibility checks, failure injection, and rollback.
- Do not rewrite rc1-rc5 historical verification records.

### Preflight: Establish the production signing key before Task 1

**External state:**
- Create or reuse: `C:\Users\asus\.chatmaker\signing\official-registry-ed25519.pem`
- Create or refresh a user-controlled backup outside the Git repository and outside every ChatMaker release/output directory.

**Requirements:**
- Generate one durable Ed25519 production private key before Task 1 starts. Never place the private key, seed, raw bytes, or backup inside the repository, worktree, logs, test fixtures, archives, or chat output.
- Treat the user as custodian. Record only the non-secret key ID, public key fingerprint, external key path and backup expectation in the implementation report.
- Task 1 derives and checks in the public trust anchor from this already-existing key. Test-only keys remain separate fixtures and can never sign the production registry.
- Every later signing step fails closed if the production key is missing or its derived public key does not match the frozen checked-in anchor. Never auto-generate a replacement key.

### Task 1: Freeze API, artifact, trust, and distribution contracts

**Files:**
- Create: `docs/architecture/llmwiki-progressive-packs.md`
- Create: `docs/contracts/llmwiki-api-v1.md`
- Create: `docs/contracts/chatcad-future-interface.md`
- Create: `packs/schemas/llmwiki-index.schema.yaml`
- Create: `packs/schemas/pack-manifest.schema.json`
- Create: `packs/schemas/registry.schema.json`
- Create: `runtime/chatmaker/trust/official_registry_keys.json`
- Create: `tests/test_llmwiki_contracts.py`

**Requirements:**
- Start with contract tests defining `index` and `section` JSON request/success/error payloads. v1 returns complete bounded sections and has no cursor.
- Freeze core artifact contents: runtime, three Skills, canonical 3/12/14 records, schemas, compact indexes, current examples, minimal installation docs, metadata and license; no detailed Wiki bodies, knowledge source workspace, tests, caches, or optional artifacts.
- Freeze three pack IDs and exact board/section-to-pack mapping.
- Freeze the official registry and signature URLs under `Amasun93/ChatMaker/main/distribution/registry`.
- Define detached signature encoding, trust-anchor lifecycle, external private-key input, registry sequence persistence, expiration, immutable commit-pinned pack URLs, and stable error codes.
- Keep ChatCAD as a future interface paragraph plus a route rejection contract only.
- Run focused contract tests and commit.

### Task 2: Establish publication governance before authoring pages

**Files:**
- Create: `knowledge_sources/README.md`
- Create: `knowledge_sources/schemas/source-manifest.schema.yaml`
- Create: `knowledge_sources/manifests/*.yaml`
- Create: `scripts/validate_knowledge_publication.py`
- Create: `tests/test_knowledge_pipeline.py`
- Modify: `.gitignore`
- Modify: `scripts/build_release.py`
- Modify: `tests/release/test_release_package.py`
- Create: `docs/contributing/knowledge-source-pipeline.md`

**Requirements:**
- Keep `knowledge_sources/raw` and `knowledge_sources/cleaned` out of Git and every release/archive.
- Require source identity, canonical URL or owned-local-source description, license/use boundary, hashes when files exist, cleaning version, review date, and separate cleaning/source/publication gates.
- Reject missing source manifests, unapproved pages, unsafe paths, malformed frontmatter, oversized pages, and unsupported schema versions.
- Seed source manifests for three boards without inventing verified status.
- Add release exclusion tests before any detailed pages are added.
- Run focused pipeline/release tests and commit.

### Task 3: Build deterministic knowledge packs and verify signed registries

**Files:**
- Create: `runtime/chatmaker/installers/registry.py`
- Create: `runtime/chatmaker/installers/pack_artifact.py`
- Create: `scripts/build_pack.py`
- Create: `scripts/sign_registry.py`
- Create: `tests/installers/test_registry.py`
- Create: `tests/installers/test_pack_artifact.py`
- Modify: `pyproject.toml`

**Requirements:**
- Start with tests for bad signature, unknown/retired key, expiration, decreasing sequence, allowlist failure, redirect origin change, wrong length/hash, zip-slip, absolute path, symlink, hook, canonical-record injection, file-count/size limits and incompatible versions.
- On Windows reject UNC, drive-relative paths, backslash traversal, ADS, reserved device names, trailing dots/spaces and case-folded duplicates.
- Verify exact registry bytes with pinned Ed25519 keys using `cryptography`; signing reads a private key only from an explicit external path and never logs it.
- Persist highest accepted sequence atomically by registry/key and reject replay after restart.
- Build deterministic `knowledge` `.cmpack` ZIPs with format version, pack ID/version, board ID, compatibility and per-file SHA-256. No hooks or dependency graph.
- Run focused tests and deterministic double-build comparison, then commit.

### Task 4: Add layered resources, atomic pack management, and automatic ensure

**Files:**
- Create: `runtime/chatmaker/resources.py`
- Create: `runtime/chatmaker/installers/pack_manager.py`
- Create: `runtime/chatmaker/pack_cli.py`
- Create: `tests/test_resource_layers.py`
- Create: `tests/installers/test_pack_manager.py`
- Modify: `pyproject.toml`

**Requirements:**
- Implement resource precedence: explicit/user override, active immutable official pack, built-in core.
- Implement `status`, `list`, `ensure`, `update`, `rollback`, and cache inspection through `chatmaker-pack`.
- Download to content-addressed `.part`, verify before extraction, validate in staging, atomically move immutable versions, rehash before activation, then atomically replace active state.
- Add a user-level lock, idempotent ensure, cached offline install, stable `offline_pack_unavailable`, rollback, interrupted-write recovery, drift quarantine, stale registry and concurrency tests.
- Do not modify Codex/WorkBuddy host configuration.
- Provide an injected transport/registry URL for deterministic local E2E tests; production defaults use the frozen official URL.
- Run focused tests and commit.

### Task 5: Author three governed board LLMWiki packs and the progressive reader

**Files:**
- Create: `packs/llmwiki/boards/arduino-nano-classic.yaml`
- Create: `packs/llmwiki/boards/arduino-uno-r3.yaml`
- Create: `packs/llmwiki/boards/esp32-devkit-v1.yaml`
- Create: `knowledge_sources/published/boards/*/*.md`
- Create: `runtime/chatmaker/llmwiki.py`
- Create: `tests/test_llmwiki.py`
- Create: `tests/test_llmwiki_validation.py`
- Modify: `pyproject.toml`

**Requirements:**
- Compact core indexes contain board ID, section metadata, consumer/topic mapping and pack ID, but no detailed section body.
- Detailed pages cite source manifests and canonical record IDs; they do not duplicate authoritative numeric pin/electrical/evidence values.
- `index` reads no optional body. `section` defaults `auto_install=true`; when the body is absent it calls idempotent `ensure(pack_id)` and then reads exactly the requested full section.
- Unknown board/consumer/section and offline/trust failures return the frozen stable errors without guessing a similar board.
- Prove first request downloads once, second request downloads zero times, cached offline request succeeds, and corrupt/replayed registry leaves the prior active version unchanged.
- Build the three deterministic `.cmpack` artifacts from approved sources and commit pack sources/artifacts before creating the signed registry.
- Run focused tests and commit.

### Task 6: Add board entry/reverse indexes and integrate current modules

**Files:**
- Modify: `runtime/chatmaker/catalog.py`
- Modify: `runtime/chatmaker/packs.py`
- Modify: `runtime/chatmaker/doctor.py`
- Modify: `skills/chatmaker/SKILL.md`
- Modify: `skills/chatduino/SKILL.md`
- Modify: `skills/chatweb/SKILL.md`
- Modify: `runtime/chatmaker/integrations/workbuddy_mcp.py`
- Modify: `tests/test_catalog.py`
- Modify: `tests/test_pack_validation.py`
- Create: `tests/test_board_context.py`
- Modify: `tests/integrations/test_workbuddy_mcp.py`
- Create: `tests/skills/test_shared_llmwiki_experience.py`

**Requirements:**
- Preserve legacy catalog golden payloads and add `open_board(board_id)` with board, compatible component, recipe and Wiki index summaries.
- Compute reverse relationships without committed duplicated board encyclopedias.
- Prove `basic-led` resolves to the same canonical path/hash before and after Wiki-pack activation and with a separately labelled local Wiki override.
- Snapshot all canonical verification objects and prove knowledge-pack installation cannot change or promote them.
- Add one MCP tool `llmwiki_get`; update its service version, exact tool count and docs in this same task.
- ChatMaker reads the start index after exact identity; ChatDuino reads safety/pins/toolchain pages plus canonical facts; ChatWeb loads web/protocol only for hardware interfaces. Independent web work does not load board knowledge.
- Add one negative test proving CAD intent does not route successfully and ChatCAD is not a specialist.
- Keep host Skill install set exactly `chatmaker/chatduino/chatweb`.
- Run focused tests and commit.

### Task 7: Build and verify the minimal core, sign the registry, and update documentation

**Files:**
- Modify: `scripts/build_release.py`
- Modify: `tests/release/test_release_package.py`
- Modify: `runtime/chatmaker/installers/codex.py`
- Modify: `runtime/chatmaker/installers/workbuddy.py`
- Modify: `tests/installers/test_codex_installer.py`
- Modify: `tests/integrations/test_workbuddy_mcp.py`
- Create: `distribution/registry/registry.json`
- Create: `distribution/registry/registry.sig.json`
- Modify: `README.md`
- Modify: `README_EN.md`
- Modify: `docs/installation.md`
- Modify: `docs/contributing/pack-format.md`
- Create: `docs/contributing/llmwiki-format.md`
- Modify: `CONTRIBUTING.md`
- Modify: `RELEASE_NOTES.md`
- Create: `docs/verification/2026-08-16-llmwiki-progressive-packs.md`

**Requirements:**
- Build deterministic `ChatMaker-Core-<version>.zip` with the frozen exact content classes; assert no optional Wiki bodies, knowledge workspace, tests or optional artifacts are inside and record its byte size/hash.
- In a fresh venv and fresh user home, install from extracted core, verify import/commands/three Skills, confirm optional sections are absent, and exercise automatic fetch against a local signed registry fixture.
- Require the preflight production private key to exist and match the frozen public anchor; fail closed on absence or mismatch. Sign the production registry without exposing the key.
- Make each production pack URL point to the exact earlier commit containing that `.cmpack`; sign and commit the registry afterward.
- Keep host installer backup/uninstall semantics and unrelated WorkBuddy MCP entries unchanged; content updates cannot edit host configuration.
- Document automatic passive knowledge installation, external/admin boundaries, local overrides, offline cache, update and rollback in beginner language.
- Do not rewrite historical rc1-rc5 evidence and do not create a public Release in this task.
- Run installer/release/clean-core tests, full documentation contract tests and commit.

### Task 8: Full review, safe merge, push, and public-download proof

**Files:**
- Modify only files required by review findings and final verification evidence.

**Requirements:**
- Run full Python tests, Playwright, Skill validation, doctor, pack validation, deterministic core/pack builds, clean-core install, local signed-registry E2E, WorkBuddy stdio listing, and `git diff --check`.
- Re-read design/plan and verify every global constraint.
- Dispatch a whole-branch code review; fix every Critical/Important issue and re-review the fix range.
- Verify feature and main worktrees are clean. Fetch origin and require `origin/main` to equal the recorded fork base; stop on unexpected remote movement rather than reset/rebase/force-push.
- Merge feature into `main`, rerun the complete suite on merged main, and create tested bootstrap commit A. Push only `main` so the signed registry and commit-pinned packs become publicly reachable.
- Confirm `git ls-remote origin refs/heads/main` equals bootstrap commit A.
- In a fresh temporary home, use the production GitHub registry URL at A to request one absent board section; prove one automatic download/activation, no second download, and cached offline access.
- Record the public URL, pack hash, registry sequence, bootstrap commit A and honest evidence limits in the tracked verification document; create evidence commit B.
- Rerun the required full verification on commit B, push only `main`, and confirm `git ls-remote origin refs/heads/main` equals the exact locally tested evidence commit B.
- Run one final read-only public smoke test against B. Report that result without making another tracked repository change.
- Mark the long goal complete only after the public-download proof succeeds.
