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
