# Task 5 report — Governed board LLMWiki packs and progressive reader

## Result

Status: DONE

Commit: `25ad1df2376872e81b3fe1025420cf3f76376719`

Commit message: `feat: add governed llmwiki board packs`

## Files and content

The focused commit contains 39 Task 5 files: 3 compact core indexes, 24
governed Markdown pages, 3 updated source manifests, 3 deterministic `.cmpack`
artifacts, the progressive reader/CLI, 2 new test modules, 1 updated pipeline
test module, the publication-validator update, and the `pyproject.toml` entry
point.

- Compact indexes: 3 boards, exactly 8 frozen sections per board, one exact
  board ID and pack ID per index, and no Markdown body field.
- Published pages: 24 total, exactly one board directory plus one Markdown
  filename below `published/boards`; each filename stem equals its
  `section_id`.
- Source manifests: 3 manifests, each with 8 exact page declarations and a
  dated derivative-page publication approval. Nano and Uno
  `source_reviewed` remain `unverified`.
- Artifacts: 3 archives, each with 9 payloads: one `llmwiki/index.yaml` and
  eight `llmwiki/sections/*.md` files.
- Canonical board/component/recipe records remain unchanged. No production
  registry or signature was created.

## TDD evidence

### Red

The first reader run was made after adding the Task 5 tests but before adding
production code:

```text
python -m unittest discover -s tests -p 'test_llmwiki.py' -v
```

Outcome: exit 1, 6 tests failed with the expected message `Task 5 LLMWiki
reader is missing`.

The content/pack tests before implementation produced the expected missing
artifact failures:

```text
python -m unittest discover -s tests -p 'test_llmwiki_validation.py' -v
```

Outcome: exit 1. The 3 compact indexes, 24 pages, 3 artifacts, and CLI entry
point were absent; the suite reported 2 assertion failures and 7 missing-file
errors.

The publication-pipeline red run was:

```text
python -m unittest discover -s tests -p 'test_knowledge_pipeline.py' -v
```

Outcome: exit 1 with 2 expected failures: checked-in page count was still zero,
and the old validator still accepted an extra nested directory. The filename
stem mismatch assertion was included in the same test.

### Green

The final focused verification ran these suites:

```text
python -m unittest discover -s tests -p 'test_llmwiki.py' -v
python -m unittest discover -s tests -p 'test_llmwiki_validation.py' -v
python -m unittest discover -s tests -p 'test_knowledge_pipeline.py' -v
python -m unittest discover -s tests -p 'test_llmwiki_contracts.py' -v
python -m unittest discover -s tests/installers -p 'test_pack_artifact.py' -v
python -m unittest discover -s tests/installers -p 'test_pack_manager.py' -v
```

Outcome: 91 tests run, 90 passed, and 1 existing Windows symlink test skipped
because the current account lacks directory-symlink privilege. There were no
Task 5 failures.

Additional final checks:

```text
python scripts/validate_knowledge_publication.py
python -m compileall -q runtime scripts
git diff --check
git diff --cached --check
```

All exited 0. Publication validation returned 3 manifests, 24 pages, zero
errors, and `success=true`.

## Progressive ensure and trust evidence

- Injected resolver/manager unit test: the first omitted-`auto_install`
  section request called `ensure` once; the second request left the cumulative
  ensure count at 1. `auto_install=false` called `ensure` zero times.
- The index request resolved availability metadata for all sections but opened
  zero section bodies.
- Each section response opened only its selected body once.
- Injected signed local registry integration test: the first section request
  fetched registry, signature, and the exact pack once. The second request and
  a cached offline request added zero transport calls; the pack-download count
  remained 1.
- A corrupt-signature update returned `registry_signature_invalid`; a replayed
  registry returned `registry_replay_detected`. Neither replaced the active
  content, and subsequent reads returned the original complete section.

## Deterministic artifact evidence

Each approved source tree was built twice with the Task 3 builder. Both builds
were compared byte-for-byte, and the checked-in artifact was then revalidated
and rebuilt by `test_llmwiki_validation.py`.

- `chatmaker-board-arduino-nano-classic-wiki-1.0.0.cmpack`
  - bytes: 10,463
  - SHA-256: `f436a6c149b9d9627f34257400854be138143d34cf928e6547a33c4366bde30a`
- `chatmaker-board-arduino-uno-r3-wiki-1.0.0.cmpack`
  - bytes: 10,291
  - SHA-256: `67110bf2e13d5ba7a9cc00235897c135ed3ee80208991d303b19330d2250a2c6`
- `chatmaker-board-esp32-devkit-v1-wiki-1.0.0.cmpack`
  - bytes: 10,471
  - SHA-256: `9cbf789ecf0598c24c9a5a238e7842366d2834c01f53887be338c8224579b34d`

## Self-review

- Confirmed every compact index contains only routing metadata and maps all
  eight unique frozen section IDs to its exact board pack.
- Confirmed index requests never call a section `read_bytes`, while section
  requests read only the selected body and return no cursor.
- Confirmed invalid request types, unknown identities, offline missing content,
  manager/trust failures, and malformed pages return frozen structured error
  codes without fuzzy fallback.
- Confirmed every page has the exact six frontmatter fields, its own board
  source reference, a bounded UTF-8 body, beginner-readable instructions, and
  canonical IDs instead of duplicated pin, voltage, toolchain, or evidence
  values.
- Confirmed Nano and Uno web pages explicitly state that the board lacks native
  Wi-Fi and needs a host or extra communication route.
- Confirmed the ESP32 web page references only `esp32-ap-led-sensor` and keeps
  upload, network, protocol, and physical-effect gates unverified.
- Confirmed publication approval is scoped to governed derivative navigation
  pages and does not promote Nano/Uno source review or any runtime gate.
- Confirmed artifacts contain only the passive index and section paths, exactly
  match approved source bytes, and no registry/signature was added.
- Confirmed the focused commit changed no canonical catalog record, Skill,
  ChatCAD runtime, mechanical data, host configuration, trust anchor, or
  production registry.

## Concerns

No Task 5 implementation concern. The production registry remains deliberately
unsigned and absent until Task 7. One existing PackManager symlink test was
skipped on this Windows account because directory-symlink creation requires a
privilege not available in the current environment; all other focused tests
passed.

## Fix Round 1

### Files changed

- `runtime/chatmaker/installers/pack_artifact.py`
- `runtime/chatmaker/installers/pack_manager.py`
- `runtime/chatmaker/llmwiki.py`
- `runtime/chatmaker/resources.py`
- `tests/test_llmwiki.py`

### Exact commands and results

```text
python -m unittest discover -s tests -p 'test_llmwiki.py' -v
```

Outcome: exit 0. Ran 10 tests, all passed. Added production-path coverage
proving the real `PackManager` + `ResourceResolver` path reads zero section
bodies for `index` and reads only the selected section body once for
`section`. Added runtime boundary coverage proving a 65,536-byte body plus
frontmatter is accepted and a 65,537-byte body is rejected.

```text
python -m unittest discover -s tests -p 'test_resource_layers.py' -v
```

Outcome: exit 0. Ran 6 tests, all passed. Confirmed resource-layer precedence
and snapshot consistency still hold after adding manifest-backed targeted
official-pack resolution.

```text
python -m unittest discover -s tests/installers -p 'test_pack_manager.py' -v
```

Outcome: exit 0. Ran 36 tests, 35 passed, 1 existing Windows symlink-privilege
skip. Confirms install/update/rollback/trust/transaction guarantees remain
intact after splitting lightweight manifest checks from full staging
verification.

```text
python -m unittest discover -s tests -p 'test_llmwiki_validation.py' -v
python -m unittest discover -s tests -p 'test_llmwiki_contracts.py' -v
python -m unittest discover -s tests -p 'test_knowledge_pipeline.py' -v
python -m unittest discover -s tests/installers -p 'test_pack_artifact.py' -v
python scripts/validate_knowledge_publication.py
python -m compileall -q runtime scripts
git diff --check
git diff --cached --check
```

Outcome: all exited 0. The focused follow-up validation passed with 5 LLMWiki
content tests, 17 contract tests, 13 publication-pipeline tests, and 14 pack
artifact tests. Publication validation returned `{"counts":{"manifests":3,
"pages":24},"errors":[],"success":true}`. `git diff --check` reported only
line-ending warnings in the working tree and no whitespace errors.

### Self-review

- Moved the production official-pack resolution path off eager
  `resource_snapshot()` payload validation and onto manifest-backed targeted
  verification, so availability checks stay metadata-only while section reads
  verify only the selected payload against the installed canonical manifest.
- Kept full-archive trust and staging verification at install/update time by
  leaving `validate_staging()` in the full store-verification path and using
  installed manifest hashes plus durable registry receipts to authenticate the
  lightweight runtime manifest path.
- Tightened runtime body-size enforcement to parse frontmatter first and apply
  the 65,536-byte ceiling only to body bytes, matching publication governance.
