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
`algorithm: ed25519`, and a canonical-base64 `signature`. Verification uses the
exact raw bytes received for `registry.json`; parsing or reserializing before
signature verification is forbidden.

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
