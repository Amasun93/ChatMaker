# Task 6 Report

## Outcome

Implemented Task 6 board-context integration for the LLMWiki progressive packs work:

- added `open_board(board_id)` to the catalog runtime with reverse component and recipe summaries plus compact Wiki index summaries
- added canonical verification snapshot support and surfaced it through `chatmaker-doctor`
- added WorkBuddy MCP tool `llmwiki_get`, bumped the MCP service version, and verified the exact tool count
- updated ChatMaker, ChatDuino, and ChatWeb Skill guidance to describe the shared LLMWiki experience and host-specific loading boundaries
- added focused regression coverage for board context, verification immutability, MCP routing, and shared-skill behavior

## Commit(s)

- `c62746b` — `Add board context and shared llmwiki integration`

## Files Changed

- `runtime/chatmaker/catalog.py`
- `runtime/chatmaker/packs.py`
- `runtime/chatmaker/doctor.py`
- `runtime/chatmaker/integrations/workbuddy_mcp.py`
- `skills/chatmaker/SKILL.md`
- `skills/chatduino/SKILL.md`
- `skills/chatweb/SKILL.md`
- `tests/test_catalog.py`
- `tests/test_pack_validation.py`
- `tests/test_board_context.py`
- `tests/integrations/test_workbuddy_mcp.py`
- `tests/skills/test_shared_llmwiki_experience.py`

## Exact Test Commands And Results

1. `python -m pytest tests/test_catalog.py tests/test_pack_validation.py tests/test_board_context.py tests/integrations/test_workbuddy_mcp.py tests/skills/test_shared_llmwiki_experience.py`
   - Result: `46 passed`

2. `python runtime/chatmaker/doctor.py`
   - Result:
     - packs `ok: true`
     - counts `board: 3`, `component: 12`, `recipe: 14`
     - `llmwiki_indexes: 3`
     - `verification_snapshot_count: 29`
     - `verification_snapshot_sha256: 771fdc359df57403aaaae198cb5ead97a7ced113318f5a33478743fec9f9b280`
     - skills `chatmaker/chatduino/chatweb` all `ok: true`

3. `python -m pytest tests/test_llmwiki_contracts.py -k "canonical_ids_counts_and_legacy_catalog_shapes_remain_unchanged or cad_intent_is_rejected_without_a_chatcad_specialist"`
   - Result: `2 passed`

4. `git diff --check`
   - Result: exit code `0`
   - Note: Git printed CRLF normalization warnings for touched files, but reported no diff-check errors.

## Requirement-By-Requirement Evidence

### Preserve legacy catalog golden payloads and add `open_board(board_id)` with board, compatible component, recipe and Wiki index summaries

- `runtime/chatmaker/catalog.py` keeps the existing `search` and `get` response shapes unchanged and adds `open_board(board_id)`.
- `tests/test_catalog.py::test_open_board_returns_reverse_indexes_and_wiki_summaries`
- `tests/test_llmwiki_contracts.py -k canonical_ids_counts_and_legacy_catalog_shapes_remain_unchanged`

### Compute reverse relationships without committed duplicated board encyclopedias

- `open_board` computes compatible components from `supported_boards` and recipes from `boards`; it does not duplicate board encyclopedias into component or recipe records.
- `tests/test_catalog.py::test_open_board_returns_reverse_indexes_and_wiki_summaries`
- `tests/test_board_context.py::test_open_board_returns_summary_only_reverse_relationships`

### Prove `basic-led` resolves to the same canonical path/hash before and after Wiki-pack activation and with a separately labelled local Wiki override

- `tests/test_board_context.py::test_basic_led_canonical_path_hash_and_verification_snapshot_survive_pack_install_and_override`
- The test verifies:
  - the canonical `basic-led` YAML path is unchanged
  - the SHA-256 hash of that canonical YAML is unchanged
  - an installed official Wiki pack does not affect canonical resolution
  - a local Wiki override is surfaced as `provenance.kind == "local_override"` with a separately labelled override path

### Snapshot all canonical verification objects and prove knowledge-pack installation cannot change or promote them

- `runtime/chatmaker/packs.py` now exposes `canonical_verification_snapshot(...)`
- `runtime/chatmaker/doctor.py` reports the canonical verification snapshot count and digest
- `tests/test_board_context.py::test_basic_led_canonical_path_hash_and_verification_snapshot_survive_pack_install_and_override`
- `tests/test_pack_validation.py::test_canonical_verification_snapshot_ignores_llmwiki_sidecars`
- `python runtime/chatmaker/doctor.py` reported the unchanged digest `771fdc359df57403aaaae198cb5ead97a7ced113318f5a33478743fec9f9b280`

### Add one MCP tool `llmwiki_get`; update its service version, exact tool count and docs in this same task

- `runtime/chatmaker/integrations/workbuddy_mcp.py` adds `llmwiki_get`
- server version updated from `1.7.0` to `1.8.0`
- exact tool count verified as `24`
- `tests/integrations/test_workbuddy_mcp.py::test_server_exposes_catalog_esp32_uno_nano_and_serial_tools_only`
- `tests/integrations/test_workbuddy_mcp.py::test_llmwiki_get_routes_index_or_section_to_shared_reader`
- `tests/integrations/test_workbuddy_mcp.py::test_initialize_routes_esp32_to_safe_compile_upload`

### ChatMaker reads the start index after exact identity; ChatDuino reads safety/pins/toolchain pages plus canonical facts; ChatWeb loads web/protocol only for hardware interfaces; independent web work does not load board knowledge

- `skills/chatmaker/SKILL.md` now instructs ChatMaker to read the `start-here` index after exact board identity
- `skills/chatduino/SKILL.md` now instructs ChatDuino to read `identify-and-safety`, `pins-and-electrical`, and `toolchains-and-upload` alongside canonical facts
- `skills/chatweb/SKILL.md` now limits board Wiki loading to hardware-interface work and states that independent classroom tools do not load board knowledge
- `tests/skills/test_shared_llmwiki_experience.py`

### Add one negative test proving CAD intent does not route successfully and ChatCAD is not a specialist

- existing route contract remains unchanged
- re-verified by `tests/test_llmwiki_contracts.py -k cad_intent_is_rejected_without_a_chatcad_specialist`

### Keep host Skill install set exactly `chatmaker/chatduino/chatweb`

- install set remains unchanged in the shared installer code
- `python runtime/chatmaker/doctor.py` reported only `chatmaker`, `chatduino`, and `chatweb`
- no ChatCAD Skill or host installer mutation was introduced in this task

### Run focused tests and commit

- focused runtime, MCP, Skill, and contract tests were run successfully as listed above
- non-amended Git commit created: `c62746b`

## Self-Review

- Caught and fixed two regressions during verification:
  - the new board-context registry fixture initially produced an invalid commit-pinned URL
  - the direct `doctor.py` entrypoint was briefly lost while adding the import fallback
- Re-ran the focused suite after each fix and re-smoked the doctor command.
- Kept canonical board/component/recipe counts at `3 / 12 / 14`.
- Did not add any ChatCAD route, Skill, MCP tool, or host installer mutation.
- Did not change canonical verification objects or legacy catalog `search/get` shapes.

## Concerns

- `git diff --check` is clean, but Git prints CRLF normalization warnings for several touched files on this Windows worktree. No content errors were reported.

## Fix Round 1

### Outcome

- added an executable ChatWeb LLMWiki routing seam in `runtime/chatmaker/route.py` so independent web work plans no board-Wiki requests while hardware-interface web work plans only `web-and-protocol`
- replaced the prose-only ChatWeb boundary test with real behavioral assertions in `tests/skills/test_shared_llmwiki_experience.py`
- strengthened the WorkBuddy install/uninstall regression in `tests/integrations/test_workbuddy_mcp.py` to assert the exact ChatMaker Skill set, preserve unrelated host files/skills, and verify the MCP initialize instructions mention the catalog plus `start-here` flow

### Exact Commands And Results

1. `python -m pytest tests/skills/test_shared_llmwiki_experience.py tests/integrations/test_workbuddy_mcp.py -q`
   - Result: `ERROR tests/skills/test_shared_llmwiki_experience.py`
   - Failure: `ImportError: cannot import name 'chatweb_llmwiki_requests_for_intent' from 'chatmaker.route'`

2. `python -m pytest tests/skills/test_shared_llmwiki_experience.py tests/integrations/test_workbuddy_mcp.py -q`
   - Result: `1 failed, 19 passed`
   - Failure: `KeyError: 'entries'` in the new WorkBuddy exact-set assertion because the test read the operation manifest instead of the referenced skill manifest

3. `python -m pytest tests/skills/test_shared_llmwiki_experience.py tests/integrations/test_workbuddy_mcp.py -q`
   - Result: `20 passed in 3.05s`

4. `python -m pytest tests/skills/test_shared_llmwiki_experience.py tests/integrations/test_workbuddy_mcp.py tests/test_llmwiki_contracts.py -q`
   - Result: `37 passed in 3.83s`

5. `git diff --check`
   - Result: exit code `0`
   - Note: Git printed LF/CRLF normalization warnings for the touched files, but no diff-check errors

### Self-Review

- kept the production change minimal: one route helper that returns exact ChatWeb LLMWiki requests instead of expanding the router contract or adding a new specialist
- verified the new boundary test is behavioral, not just string-matching prose in `skills/chatweb/SKILL.md`
- verified the WorkBuddy regression now checks the exact installed ChatMaker Skill manifest while preserving an unrelated Skill directory, unrelated MCP config, and an unrelated host settings file
- kept scope inside the reviewer’s two Important findings plus the related MCP initialize documentation assertion

### Concerns

- `git diff --check` is clean, but Git still reports LF/CRLF normalization warnings for the edited files on this Windows worktree
