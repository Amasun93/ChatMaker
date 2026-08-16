---
schema_version: "1.0"
kind: knowledge-page
stable_id: arduino-uno-r3-troubleshooting
board_id: arduino-uno-r3
section_id: troubleshooting
source_refs:
  - source-arduino-uno-r3-documentation
---
# Find the earliest unsupported claim

Reload canonical `arduino-uno-r3`, every selected component ID, and the recipe ID. Identify the first failing or unproven gate among environment, identity, wiring, compile, upload, runtime, and physical effect. Check that gate without altering later statuses. Apply one reversible change, repeat the same observation, and report only what the new evidence demonstrates; never guess a similar board or port.
