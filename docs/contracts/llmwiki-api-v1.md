# LLMWiki JSON API v1

The CLI and WorkBuddy MCP use the same object requests and responses. Unknown
IDs fail without fuzzy matching. `index` never reads an optional section body.
`section` defaults `auto_install` to `true` when omitted and returns one full
UTF-8 body of at most 65,536 bytes. v1 has no pagination and the key `cursor`
is invalid at every level.

## Index request

Required string fields are `action=index`, `board_id`, and `consumer`.
Consumers are `chatmaker`, `chatduino`, or `chatweb`.

<!-- contract:index.request -->
```json
{
  "action": "index",
  "board_id": "arduino-nano-classic",
  "consumer": "chatduino"
}
```

## Index success

`available` reports whether the detailed body is currently readable. The index
itself is core metadata, so `available=false` is still a successful response.
`provenance` is `builtin_core`, `official_pack`, or `local_override`.

<!-- contract:index.success -->
```json
{
  "success": true,
  "api_version": "1",
  "action": "index",
  "board_id": "arduino-nano-classic",
  "consumer": "chatduino",
  "sections": [
    {"section_id": "start-here", "title": "Start here", "summary": "Choose the exact board and workflow.", "topics": ["identity", "workflow"], "pack_id": "chatmaker-board-arduino-nano-classic-wiki", "available": false, "provenance": "builtin_core"},
    {"section_id": "identify-and-safety", "title": "Identify and safety", "summary": "Confirm identity and review safety boundaries.", "topics": ["identity", "safety"], "pack_id": "chatmaker-board-arduino-nano-classic-wiki", "available": false, "provenance": "builtin_core"},
    {"section_id": "pins-and-electrical", "title": "Pins and electrical", "summary": "Use canonical pin and electrical facts safely.", "topics": ["pins", "electrical"], "pack_id": "chatmaker-board-arduino-nano-classic-wiki", "available": false, "provenance": "builtin_core"},
    {"section_id": "toolchains-and-upload", "title": "Toolchains and upload", "summary": "Select, compile and upload with separate evidence.", "topics": ["toolchain", "compile", "upload"], "pack_id": "chatmaker-board-arduino-nano-classic-wiki", "available": false, "provenance": "builtin_core"},
    {"section_id": "components-and-wiring", "title": "Components and wiring", "summary": "Resolve canonical components and wiring constraints.", "topics": ["components", "wiring"], "pack_id": "chatmaker-board-arduino-nano-classic-wiki", "available": false, "provenance": "builtin_core"},
    {"section_id": "libraries-and-examples", "title": "Libraries and examples", "summary": "Choose libraries and current examples.", "topics": ["libraries", "examples"], "pack_id": "chatmaker-board-arduino-nano-classic-wiki", "available": false, "provenance": "builtin_core"},
    {"section_id": "web-and-protocol", "title": "Web and protocol", "summary": "Load only for hardware-web communication work.", "topics": ["web", "protocol"], "pack_id": "chatmaker-board-arduino-nano-classic-wiki", "available": false, "provenance": "builtin_core"},
    {"section_id": "troubleshooting", "title": "Troubleshooting", "summary": "Diagnose failures without merging evidence gates.", "topics": ["diagnosis", "evidence"], "pack_id": "chatmaker-board-arduino-nano-classic-wiki", "available": false, "provenance": "builtin_core"}
  ]
}
```

## Index error

An index failure echoes only the index request identity fields and the common
error object. It never includes `section_id`, `sections`, a guessed board, or a
cursor.

<!-- contract:index.error -->
```json
{
  "success": false,
  "api_version": "1",
  "action": "index",
  "board_id": "arduino-nano-clasic",
  "consumer": "chatduino",
  "error": {
    "code": "llmwiki_board_not_found",
    "message": "Unknown board_id: arduino-nano-clasic",
    "retryable": false
  }
}
```

## Section request

`auto_install` is optional and defaults to `true`. If false and no installed or
override body exists, return `offline_pack_unavailable` without network access.

<!-- contract:section.request -->
```json
{
  "action": "section",
  "board_id": "arduino-nano-classic",
  "consumer": "chatduino",
  "section_id": "identify-and-safety",
  "auto_install": true
}
```

## Section success

`body_bytes` is the UTF-8 byte count, `max_body_bytes` is always 65536 in v1,
and `complete` is always true. A truncated body is never a successful result.

<!-- contract:section.success -->
```json
{
  "success": true,
  "api_version": "1",
  "action": "section",
  "board_id": "arduino-nano-classic",
  "consumer": "chatduino",
  "section_id": "identify-and-safety",
  "title": "Identify and safety",
  "body": "Confirm board identity before wiring.",
  "body_bytes": 37,
  "max_body_bytes": 65536,
  "complete": true,
  "provenance": {
    "kind": "official_pack",
    "pack_id": "chatmaker-board-arduino-nano-classic-wiki",
    "version": "1.0.0"
  }
}
```

For a local override, provenance is `{"kind":"local_override",
"path":"<user-owned relative label>"}`. Built-in safety content uses
`{"kind":"builtin_core","core_version":"<version>"}`. Filesystem absolute
paths are not exposed in normal responses.

## Error

Every failure uses the same `error` object. `message` is diagnostic text and is
not a programmatic contract. `retryable` is true only when retrying without
changing identity or trust policy can succeed. Relevant request identity fields
are echoed exactly; no suggested or substituted board is returned.

<!-- contract:section.error -->
```json
{
  "success": false,
  "api_version": "1",
  "action": "section",
  "board_id": "arduino-nano-clasic",
  "consumer": "chatduino",
  "section_id": "identify-and-safety",
  "error": {
    "code": "llmwiki_board_not_found",
    "message": "Unknown board_id: arduino-nano-clasic",
    "retryable": false
  }
}
```

Stable API identity errors are `invalid_llmwiki_request`,
`unknown_llmwiki_action`, `llmwiki_board_not_found`,
`llmwiki_consumer_not_supported`, and `llmwiki_section_not_found`. Section reads
also forward the stable distribution/trust errors listed in the architecture
contract without renaming them.

<!-- contract:error.codes -->
```json
[
  "invalid_llmwiki_request",
  "unknown_llmwiki_action",
  "llmwiki_board_not_found",
  "llmwiki_consumer_not_supported",
  "llmwiki_section_not_found",
  "offline_pack_unavailable",
  "registry_fetch_failed",
  "registry_signature_invalid",
  "registry_key_unknown",
  "registry_key_retired",
  "registry_key_not_yet_valid",
  "registry_key_expired",
  "registry_expired",
  "registry_replay_detected",
  "pack_not_allowlisted",
  "pack_incompatible",
  "pack_download_failed",
  "pack_redirect_origin_changed",
  "pack_size_mismatch",
  "pack_hash_mismatch",
  "pack_archive_unsafe",
  "pack_manifest_invalid",
  "pack_content_invalid",
  "pack_drift_detected",
  "pack_activation_failed"
]
```
