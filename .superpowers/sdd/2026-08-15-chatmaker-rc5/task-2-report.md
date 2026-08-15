# Task 2 Report

## Status

Completed in `D:\Projects\ChatMaker\.worktrees\codex-rc5-release` on branch `codex/rc5-release`.

## Scope Delivered

- Added deterministic `chatmaker-route` runtime and CLI in `runtime/chatmaker/route.py`.
- Added `chatmaker-route` script entry to `pyproject.toml`.
- Added route behavior tests for hardware, web, ambiguous, combined-without-contract, combined-with-contract, and CLI execution.
- Changed `catalog_get` to resolve the exact `<id>.yaml` path instead of loading unrelated records.
- Added record caching in `runtime/chatmaker/packs.py` so unchanged YAML is not reread unnecessarily across repeated operations.
- Expanded verification-gate validation to every verification entry, including extension gates.
- Updated board/component/recipe schemas so extension gates must use the same gate schema as baseline gates.
- Documented recipe-specific extension gates in `docs/contributing/pack-format.md` without making them universal across boards/components.

## Files Changed

- `runtime/chatmaker/route.py`
- `runtime/chatmaker/catalog.py`
- `runtime/chatmaker/packs.py`
- `pyproject.toml`
- `packs/schemas/board.schema.yaml`
- `packs/schemas/component.schema.yaml`
- `packs/schemas/recipe.schema.yaml`
- `docs/contributing/pack-format.md`
- `tests/test_route.py`
- `tests/test_catalog.py`
- `tests/test_pack_validation.py`

## TDD Notes

- Wrote new route, catalog, and extension-gate tests first.
- Confirmed red failures:
  - missing `chatmaker.route`
  - `catalog_get` loading unrelated YAML
  - extension gates bypassing validation
- Implemented the minimal runtime/schema changes to make those tests pass.

## Validation

- `python -m unittest discover -s tests -p 'test_route.py' -v`
- `python -m unittest discover -s tests -p 'test_catalog.py' -v`
- `python -m unittest discover -s tests -p 'test_pack_validation.py' -v`
- `git diff --check`

All focused tests passed. `git diff --check` passed with only line-ending warnings from Git's working-copy normalization.

## Constraints Checked

- Preserved the thin ChatMaker / ChatDuino / ChatWeb boundary.
- Combined routing requires an explicit transport and at least one request/response or message interaction.
- Router keeps page-rendering evidence separate from hardware verification.
- Did not touch the old Nano repository.
- Preserved the untracked plan file `docs/superpowers/plans/2026-08-15-chatmaker-rc5.md`.

## Concerns

- `catalog_get` now depends on the repository convention that record filenames match stable record IDs. That matches the current pack layout and the new regression test, but future catalog records should keep that convention.
- `git diff --check` surfaced LF/CRLF normalization warnings only; there were no whitespace errors.

## Round 1 Fix: Stable ID Lookup

- Replaced filename-based `catalog_get` lookup with a cached stable-ID to path index built from pack-file metadata plus per-file `id` extraction.
- The index cache is invalidated when the pack file set, mtimes, or sizes change.
- Added a regression test where `id: target-record` lives in `target-record-v2.yaml` and verified that unrelated records are never passed to `load_record`.

### Exact Commands And Output

```text
> python -m unittest discover -s tests -p 'test_catalog.py' -v
test_catalog_runtime_exists (test_catalog.CatalogTests.test_catalog_runtime_exists) ... ok
test_get_loads_only_the_requested_record_path (test_catalog.CatalogTests.test_get_loads_only_the_requested_record_path) ... ok
test_get_returns_the_full_record_and_evidence_gates (test_catalog.CatalogTests.test_get_returns_the_full_record_and_evidence_gates) ... ok
test_get_uses_stable_id_even_when_filename_differs (test_catalog.CatalogTests.test_get_uses_stable_id_even_when_filename_differs) ... FAIL
test_json_cli_searches_the_checked_in_catalog (test_catalog.CatalogTests.test_json_cli_searches_the_checked_in_catalog) ... ok
test_search_finds_a_component_by_chinese_alias (test_catalog.CatalogTests.test_search_finds_a_component_by_chinese_alias) ... ok

======================================================================
FAIL: test_get_uses_stable_id_even_when_filename_differs (test_catalog.CatalogTests.test_get_uses_stable_id_even_when_filename_differs)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\Projects\ChatMaker\.worktrees\codex-rc5-release\tests\test_catalog.py", line 125, in test_get_uses_stable_id_even_when_filename_differs
    self.assertTrue(result["success"], result)
AssertionError: False is not true : {'success': False, 'action': 'get', 'error': 'catalog_record_not_found', 'id': 'target-record'}

----------------------------------------------------------------------
Ran 6 tests in 1.051s

FAILED (failures=1)
```

```text
> python -m unittest discover -s tests -p 'test_catalog.py' -v
test_catalog_runtime_exists (test_catalog.CatalogTests.test_catalog_runtime_exists) ... ok
test_get_loads_only_the_requested_record_path (test_catalog.CatalogTests.test_get_loads_only_the_requested_record_path) ... ok
test_get_returns_the_full_record_and_evidence_gates (test_catalog.CatalogTests.test_get_returns_the_full_record_and_evidence_gates) ... ok
test_get_uses_stable_id_even_when_filename_differs (test_catalog.CatalogTests.test_get_uses_stable_id_even_when_filename_differs) ... ok
test_json_cli_searches_the_checked_in_catalog (test_catalog.CatalogTests.test_json_cli_searches_the_checked_in_catalog) ... ok
test_search_finds_a_component_by_chinese_alias (test_catalog.CatalogTests.test_search_finds_a_component_by_chinese_alias) ... ok

----------------------------------------------------------------------
Ran 6 tests in 1.127s

OK
```

```text
> python -m unittest discover -s tests -p 'test_pack_validation.py' -v
test_checked_in_pack_repository_is_valid (test_pack_validation.PackValidationTests.test_checked_in_pack_repository_is_valid) ... ok
test_component_learning_fields_are_required (test_pack_validation.PackValidationTests.test_component_learning_fields_are_required) ... ok
test_duplicate_ids_fail_even_across_record_kinds (test_pack_validation.PackValidationTests.test_duplicate_ids_fail_even_across_record_kinds) ... ok
test_esp32_board_record_keeps_module_and_carrier_identity_separate (test_pack_validation.PackValidationTests.test_esp32_board_record_keeps_module_and_carrier_identity_separate) ... ok
test_esp32_external_led_recipe_avoids_boot_strapping_pin (test_pack_validation.PackValidationTests.test_esp32_external_led_recipe_avoids_boot_strapping_pin) ... ok
test_first_component_pack_contains_the_planned_twelve_modules (test_pack_validation.PackValidationTests.test_first_component_pack_contains_the_planned_twelve_modules) ... ok
test_migrated_nano_examples_have_recipe_records (test_pack_validation.PackValidationTests.test_migrated_nano_examples_have_recipe_records) ... ok
test_missing_component_example_file_fails (test_pack_validation.PackValidationTests.test_missing_component_example_file_fails) ... ok
test_missing_recipe_source_file_fails (test_pack_validation.PackValidationTests.test_missing_recipe_source_file_fails) ... ok
test_pin_conflict_fails_unless_the_connection_is_shared (test_pack_validation.PackValidationTests.test_pin_conflict_fails_unless_the_connection_is_shared) ... ok
test_recipe_extension_gate_must_use_the_same_gate_schema (test_pack_validation.PackValidationTests.test_recipe_extension_gate_must_use_the_same_gate_schema) ... ok
test_recipe_extension_gate_with_full_gate_shape_is_valid (test_pack_validation.PackValidationTests.test_recipe_extension_gate_with_full_gate_shape_is_valid) ... ok
test_unknown_board_and_component_references_fail (test_pack_validation.PackValidationTests.test_unknown_board_and_component_references_fail) ... ok
test_unknown_component_and_board_pins_fail (test_pack_validation.PackValidationTests.test_unknown_component_and_board_pins_fail) ... ok
test_uno_blink_has_a_dedicated_recipe_and_source_file (test_pack_validation.PackValidationTests.test_uno_blink_has_a_dedicated_recipe_and_source_file) ... ok
test_valid_repository_reports_record_counts (test_pack_validation.PackValidationTests.test_valid_repository_reports_record_counts) ... ok
test_verified_gate_requires_dated_evidence (test_pack_validation.PackValidationTests.test_verified_gate_requires_dated_evidence) ... ok

----------------------------------------------------------------------
Ran 17 tests in 1.341s

OK
```

```text
> git diff --check
warning: in the working copy of 'runtime/chatmaker/catalog.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_catalog.py', LF will be replaced by CRLF the next time Git touches it
```
