# ChatMaker Knowledge Rename Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current knowledge-layer identity with ChatMaker Knowledge everywhere, preserve canonical facts, and migrate existing user state without retaining legacy API aliases.

**Architecture:** Freeze one new Knowledge contract, migrate runtime and passive pack paths together, then rebuild all official packs. A one-time state migrator backs up and deactivates prior pack identities so an upgrade never treats valid old state as corruption.

**Tech Stack:** Python 3.11, YAML/JSON Schema, unittest, deterministic ZIP packs, Ed25519 registry signatures.

## Global Constraints

- User-facing names are `ChatMaker Knowledge` and `ChatMaker 知识库`.
- Stable entry points are `chatmaker-knowledge`, `knowledge_get`, `chatmaker.knowledge`, and `knowledge/boards`.
- Do not retain old CLI, MCP, Python-module, schema, error-code, field, or pack-ID aliases.
- Preserve existing board/component/recipe IDs and their evidence states.
- Back up and deactivate legacy installed pack state; do not silently delete old cache, store, or overrides.
- Current tracked source, paths, Skills, Core, and `.cmpack` payloads must contain no old knowledge-layer name.
- Production signing keys remain outside the repository and must never be printed or copied.

---

### Task 1: Freeze the new Knowledge contract

**Files:**
- Create: `docs/contracts/knowledge-api-v1.md`
- Create: `docs/contributing/knowledge-format.md`
- Create: `packs/schemas/knowledge-index.schema.yaml`
- Create: `tests/test_knowledge_contracts.py`
- Create: `tests/test_knowledge_validation.py`
- Remove after replacement: old contract, format, and schema paths

**Interfaces:**
- Produces: `knowledge-index`, `knowledge-page`, `knowledge_index_schema`, `knowledge/*` payload paths, and `*_knowledge_*` identity errors.

- [ ] **Step 1: Write failing contract tests** asserting exact names, the eight section IDs, body limit 65,536 bytes, and absence of old identifiers.
- [ ] **Step 2: Run** `python -m unittest tests.test_knowledge_contracts tests.test_knowledge_validation -v` and confirm failures identify missing new files.
- [ ] **Step 3: Author the schema and contract** with examples such as:

```json
{"action":"section","board_id":"arduino-nano-classic","consumer":"chatduino","section_id":"start-here","auto_install":true}
```

- [ ] **Step 4: Run the focused tests** and confirm they pass.
- [ ] **Step 5: Commit** `test: freeze ChatMaker Knowledge contract`.

### Task 2: Migrate semantic validation and reader

**Files:**
- Create: `runtime/chatmaker/knowledge_semantics.py`
- Create: `runtime/chatmaker/knowledge.py`
- Create: `tests/test_knowledge.py`
- Remove after callers migrate: `runtime/chatmaker/llmwiki.py`, `runtime/chatmaker/llmwiki_semantics.py`, and old test paths

**Interfaces:**
- Produces: `execute_request(request, *, manager=None, resolver=None, project_root=None) -> dict[str, Any]`.
- Produces: `BOARD_IDS`, `SECTION_IDS`, `PACK_IDS`, `validate_index_bytes`, `validate_page_bytes`, and `validate_pack_payload`.

- [ ] **Step 1: Rename tests first** and replace expected module, kind, payload path, pack ID, and error identities.
- [ ] **Step 2: Run** `python -m unittest tests.test_knowledge -v` and confirm import/identity failures.
- [ ] **Step 3: Implement the new modules** by preserving reader behavior while changing identities. New pack IDs follow `chatmaker-board-<board-id>-knowledge` and resources follow `knowledge/index.yaml` and `knowledge/sections/<section-id>.md`.
- [ ] **Step 4: Confirm unknown identities return** `invalid_knowledge_request`, `unknown_knowledge_action`, `knowledge_board_not_found`, `knowledge_consumer_not_supported`, or `knowledge_section_not_found`.
- [ ] **Step 5: Run focused tests** and commit `refactor: migrate knowledge reader identity`.

### Task 3: Migrate runtime consumers and Skills

**Files:**
- Modify: `runtime/chatmaker/catalog.py`
- Modify: `runtime/chatmaker/doctor.py`
- Modify: `runtime/chatmaker/resources.py`
- Modify: `runtime/chatmaker/route.py`
- Modify: `runtime/chatmaker/integrations/workbuddy_mcp.py`
- Modify: `skills/chatmaker/SKILL.md`
- Modify: `skills/chatduino/SKILL.md`
- Modify: `pyproject.toml`
- Rename/update consumer tests under `tests/`, `tests/skills/`, and `tests/integrations/`

**Interfaces:**
- Produces: `knowledge_requests`, `knowledge` catalog data, `knowledge_indexes` doctor data, CLI `chatmaker-knowledge`, MCP `knowledge_get`.

- [ ] **Step 1: Change consumer expectations first**, including MCP version `1.9.0` and unchanged total tool count 24.
- [ ] **Step 2: Run focused consumer tests** and confirm failures reference old fields/tools.
- [ ] **Step 3: Update runtime imports, response fields, route helpers, descriptions, and Skill commands** in one migration.
- [ ] **Step 4: Run** `python -m unittest tests.test_board_context tests.test_catalog tests.test_route tests.skills.test_shared_knowledge_experience tests.integrations.test_workbuddy_mcp -v`.
- [ ] **Step 5: Commit** `refactor: route all consumers through ChatMaker Knowledge`.

### Task 4: Migrate indexes, pages, pack builder, and resolver

**Files:**
- Create: `knowledge/boards/*.yaml`
- Modify: all 24 files under `knowledge_sources/published/boards/`
- Modify: `runtime/chatmaker/installers/pack_artifact.py`
- Modify: `runtime/chatmaker/installers/pack_manager.py`
- Modify: `scripts/build_pack.py`
- Modify: `scripts/build_release.py`
- Modify: `scripts/validate_knowledge_publication.py`
- Remove: `packs/llmwiki/`
- Modify: installer, validation, resource, and release tests

**Interfaces:**
- Consumes: Task 1 schema and Task 2 semantic validators.
- Produces: deterministic passive packs whose only payload paths are `knowledge/index.yaml` and `knowledge/sections/*.md`.

- [ ] **Step 1: Update failing pack tests** for the new directory, manifest compatibility field, and safe-extraction aliases.
- [ ] **Step 2: Run** `python -m unittest tests.installers.test_pack_artifact tests.installers.test_pack_manager tests.test_resource_layers tests.test_knowledge_pipeline -v`.
- [ ] **Step 3: Move compact indexes, update page frontmatter, and update all builders/resolvers** without changing the 8-section bodies or canonical facts.
- [ ] **Step 4: Build each existing pack twice** and assert byte-identical archives and SHA-256 values.
- [ ] **Step 5: Commit** `refactor: migrate passive packs to Knowledge format`.

### Task 5: Safely migrate existing user state

**Files:**
- Create: `runtime/chatmaker/installers/knowledge_state_migration.py`
- Create: `tests/installers/test_knowledge_state_migration.py`
- Modify: `runtime/chatmaker/installers/pack_manager.py`

**Interfaces:**
- Produces: `migrate_legacy_knowledge_state(paths: PackPaths) -> MigrationResult`.
- `MigrationResult` contains `changed`, `backup_dir`, `deactivated_pack_ids`, and `preserved_paths`.

- [ ] **Step 1: Write tests** with prior pack IDs in `active.json`, `installed-packs.json`, cache receipts, store, and overrides.
- [ ] **Step 2: Verify tests fail** because the new allowlist rejects prior state.
- [ ] **Step 3: Implement one locked, idempotent migration** that byte-for-byte backs up state files, removes prior identities only from active/installed metadata, preserves legacy data on disk, and records a migration marker.
- [ ] **Step 4: Inject failure before replacement** and prove original state remains byte-identical.
- [ ] **Step 5: Run migration and pack-manager tests** and commit `feat: migrate prior knowledge pack state safely`.

### Task 6: Remove old current-tree identity and refresh docs

**Files:**
- Rename/update current architecture, plan, verification, README, installation, contribution, release-note, and knowledge-source documents.
- Remove superseded current-tree historical snapshots whose claims cannot be truthfully renamed; Git history remains the record.

**Interfaces:**
- Produces: a current tree with no old knowledge-layer string in tracked text or tracked paths.

- [ ] **Step 1: Add a release validation command** that scans tracked text, paths, Skills, and archive manifests; keep it outside the behavioral unittest suite.
- [ ] **Step 2: Update current documentation** without rewriting old hashes or claims as though the new identity existed previously.
- [ ] **Step 3: Run** `git grep -n -I -i -E 'llmwiki|llm wiki'` and `git ls-files | rg -i 'llmwiki'`; both must return no matches.
- [ ] **Step 4: Convert this migration plan into a concise completion record using generic legacy-layer wording**, so the plan itself also passes the final naming scan while its original detail remains available in Git history.
- [ ] **Step 5: Run the complete Python and browser suites**, then commit `docs: complete ChatMaker Knowledge naming migration`.
