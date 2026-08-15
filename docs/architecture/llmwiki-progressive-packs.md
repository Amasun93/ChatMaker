# LLMWiki progressive knowledge-pack architecture

## Boundary

Canonical board, component, recipe and verification facts remain in the core
`packs/boards`, `packs/components` and `packs/recipes` records. LLMWiki adds
bounded explanatory pages that refer to those stable IDs; it does not copy or
promote canonical values. Installing knowledge therefore cannot alter evidence
for environment, source, compile, upload, serial/browser, network, power-cycle,
mechanical or physical-effect gates.

The core artifact contains exactly the runtime, the `chatmaker`, `chatduino`
and `chatweb` Skills, the canonical 3 board/12 component/14 recipe records,
schemas, compact LLMWiki indexes, current examples, minimal installation docs,
package metadata and the Apache-2.0 license. It excludes detailed Wiki bodies,
`knowledge_sources`, tests, caches, build workspaces, downloaded archives and
all other optional artifacts.

Optional packs are passive, read-only `knowledge` packs. Their archive entries
are limited to an LLMWiki index and Markdown sections under `llmwiki/`. They
cannot contain canonical records, dependencies or install hooks.

## Frozen board and section mapping

Every section below is complete and no larger than 65,536 UTF-8 bytes. The
mapping is intentionally identical across the three initial boards so callers
can ask for a stable topic after confirming an exact board ID.

```json
{
  "arduino-nano-classic": {
    "pack_id": "chatmaker-board-arduino-nano-classic-wiki",
    "section_ids": [
      "start-here",
      "identify-and-safety",
      "pins-and-electrical",
      "toolchains-and-upload",
      "components-and-wiring",
      "libraries-and-examples",
      "web-and-protocol",
      "troubleshooting"
    ]
  },
  "arduino-uno-r3": {
    "pack_id": "chatmaker-board-arduino-uno-r3-wiki",
    "section_ids": [
      "start-here",
      "identify-and-safety",
      "pins-and-electrical",
      "toolchains-and-upload",
      "components-and-wiring",
      "libraries-and-examples",
      "web-and-protocol",
      "troubleshooting"
    ]
  },
  "esp32-devkit-v1": {
    "pack_id": "chatmaker-board-esp32-devkit-v1-wiki",
    "section_ids": [
      "start-here",
      "identify-and-safety",
      "pins-and-electrical",
      "toolchains-and-upload",
      "components-and-wiring",
      "libraries-and-examples",
      "web-and-protocol",
      "troubleshooting"
    ]
  }
}
```

Compact indexes contain only section metadata, consumer/topic routing and the
pack ID. Detailed bodies remain outside the core.

## Distribution and trust

The official mutable discovery endpoints are:

- `https://raw.githubusercontent.com/Amasun93/ChatMaker/main/distribution/registry/registry.json`
- `https://raw.githubusercontent.com/Amasun93/ChatMaker/main/distribution/registry/registry.sig.json`

`registry.sig.json` is a detached JSON object with only `key_id`,
`algorithm: ed25519`, and a canonical-base64 `signature`. The signature is
exactly 64 bytes encoded as 88 ASCII characters: 85 base64 alphabet
characters, a final data character from `A`, `Q`, `g`, or `w`, then `==`.
Decoding is strict, must yield exactly 64 bytes, and re-encoding must reproduce
the input exactly; aliases with nonzero pad bits are rejected. Verification
uses the exact raw bytes received for `registry.json`; parsing or reserializing
before signature verification is forbidden.

The core pins public keys by key ID. A key is accepted only while active and
inside its `not_before`/`not_after` window. Rotation adds the replacement
anchor in a new core before it signs a registry; retirement or emergency
revocation requires a core update. The production signing command receives the
custodian-owned external input
`C:\Users\asus\.chatmaker\signing\official-registry-ed25519.pem`; the key and
its user-controlled backup must remain outside the repository and every
release/output directory. A registry signed by an unknown, retired,
not-yet-valid or expired key fails closed. Private keys are accepted only from
that explicit repository-external path supplied to the signing command. Signing
never generates a key, prints private material or copies it into an artifact.

Each registry has a positive monotonic `sequence`, `generated_at` and
`expires_at`. The client atomically persists the highest accepted sequence
scoped by the pair `(registry_url, key_id)` and rejects any lower sequence,
including after restart. Expired registries are rejected; a previously
verified installed pack may remain active for offline reads, but stale metadata
cannot authorize a new install or update.

Registry discovery is allowed only at the two frozen `main` URLs above. Pack
entries must use HTTPS raw GitHub URLs pinned to the exact 40-character commit
that contains the archive. Redirects may not change origin. Each entry pins
length, SHA-256 and explicit core/schema compatibility.

## Deterministic pack archive

A `.cmpack` is an uncompressed ZIP with one generated `pack-manifest.json`
entry followed by the manifest's payload files. `pack-manifest.json` is not
listed in its own `files` array. Payload paths are the validated ASCII POSIX
paths accepted by the manifest schema, and duplicate `files[].path` values are
rejected by semantic validation even when their length or hash differs. The
public error remains `pack_manifest_invalid` with reason `duplicate_path` and
the repeated path. Path comparison at this layer is exact Unicode code-point
comparison; the later safe-extraction layer additionally rejects platform
aliases and case-folded duplicates.

<!-- contract:manifest.duplicate-path.error -->
```json
{
  "error": {
    "code": "pack_manifest_invalid",
    "reason": "duplicate_path",
    "path": "llmwiki/sections/identify-and-safety.md"
  }
}
```

The builder validates source bytes before archiving and never rewrites them.
All archive metadata and ordering follow this contract:

<!-- contract:archive.determinism -->
```json
{
  "format": "zip",
  "compression": "stored",
  "entry_order": "pack-manifest.json then payload paths by UTF-8 byte order",
  "timestamp": "1980-01-01T00:00:00",
  "create_system": 3,
  "unix_mode": "0100644",
  "extra": "",
  "comment": "",
  "directory_entries": false,
  "manifest_json": "UTF-8; sorted keys; separators comma/colon; one trailing LF",
  "manifest_files_order": "payload paths by UTF-8 byte order",
  "payload_bytes": "exact validated source bytes",
  "repeat_build_invariant": "byte-identical archive and SHA-256"
}
```

In concrete writer terms, every entry uses ZIP method `stored`, DOS timestamp
`(1980, 1, 1, 0, 0, 0)`, `create_system=3`, regular-file mode `0100644`, and
empty per-entry extra/comment fields; the archive comment is empty and there
are no directory entries. Before serialization, the manifest `files` array is
sorted by the same UTF-8 path-byte order used for ZIP payload entries. The
manifest bytes are
`json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))`
encoded as UTF-8 plus one LF. A second build from identical validated inputs
must produce byte-identical archive bytes and the same SHA-256.

## Installation transaction and authority

Silent installation is limited to allowlisted pack IDs in the mapping above,
signed by an accepted official key, with `pack_type=knowledge`, into a
user-owned ChatMaker directory. The manager downloads to a content-addressed
`.part`, verifies trust/compatibility/length/hash, safely extracts to staging,
validates every file, atomically moves an immutable version into the store,
rehashes it, and atomically replaces active state. Failure leaves the prior
active version unchanged. Drift in an official immutable directory is
quarantined. Explicit local overrides remain separate, take precedence and are
reported with `provenance=local_override`.

Failure injection is a test-only dependency at the named boundaries below.
When enabled, the named boundary raises `failure_injected`, runs no subsequent
phase, and must preserve every listed invariant. `before_sequence_replace` is
immediately before the atomic registry-sequence state replacement;
`after_sequence_replace` is after the new value is durable. Pack points are
after the named completed phase, except `before_active_replace`, which is
immediately before the active-state replacement. `after_active_replace`
simulates a failure after the new active state becomes durable and therefore
exercises compensating rollback.

<!-- contract:transaction.failure-injection -->
```json
{
  "points": [
    "registry.before_sequence_replace",
    "registry.after_sequence_replace",
    "pack.after_part_write",
    "pack.after_archive_verify",
    "pack.after_staging_extract",
    "pack.after_staging_validate",
    "pack.after_store_move",
    "pack.before_active_replace",
    "pack.after_active_replace"
  ],
  "injected_error": "failure_injected",
  "invariants": [
    "no unverified version becomes active",
    "failure through pack.before_active_replace leaves active.json byte-identical",
    "failure at pack.after_active_replace atomically restores prior active.json",
    "rollback targets only a rehashed previously verified immutable version",
    "registry sequence never decreases during install or rollback",
    "registry.before_sequence_replace preserves the old sequence",
    "registry.after_sequence_replace preserves the new higher sequence",
    "verified cache/store data may remain inactive and must be reverified before reuse",
    "partial/staging data is never active and is ignored or cleaned on retry",
    "explicit local overrides are unchanged"
  ]
}
```

The prior `active.json` includes the no-active-file state: if none existed, a
failure through `before_active_replace` leaves none, and compensating rollback
after replacement removes the new file atomically. A verified immutable store
directory may remain inactive after `after_store_move`; rollback never deletes
or edits a previously verified immutable version. Registry sequence state is a
separate security monotonicity boundary and is never rolled back with pack
activation.

The pack manager never silently installs drivers, toolchains, Arduino cores,
Mind+, Node or browsers; edits PATH; requests elevation; changes WorkBuddy MCP
configuration; or runs hooks. Those operations retain their existing explicit
consent and evidence boundaries.

## Stable trust and install errors

The stable v1 codes are `invalid_llmwiki_request`, `unknown_llmwiki_action`,
`llmwiki_board_not_found`, `llmwiki_consumer_not_supported`,
`llmwiki_section_not_found`, `offline_pack_unavailable`,
`registry_fetch_failed`, `registry_signature_invalid`, `registry_key_unknown`,
`registry_key_retired`, `registry_key_not_yet_valid`, `registry_key_expired`,
`registry_expired`, `registry_replay_detected`, `pack_not_allowlisted`,
`pack_incompatible`, `pack_download_failed`, `pack_redirect_origin_changed`,
`pack_size_mismatch`, `pack_hash_mismatch`, `pack_archive_unsafe`,
`pack_manifest_invalid`, `pack_content_invalid`, `pack_drift_detected`, and
`pack_activation_failed`. The API error envelope is frozen in
`docs/contracts/llmwiki-api-v1.md`.
