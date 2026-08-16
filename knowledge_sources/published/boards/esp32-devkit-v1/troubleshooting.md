---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-devkit-v1-troubleshooting
board_id: esp32-devkit-v1
section_id: troubleshooting
source_refs:
  - source-esp32-devkit-v1-doit-board-definition
---
# Troubleshoot in evidence order

Reload canonical `esp32-devkit-v1`, selected component IDs, and the active recipe ID. Find the first failing or unproven gate among environment, carrier identity, wiring, compile, upload, reboot, runtime, network, protocol, and physical effect. Inspect only that boundary and preserve later statuses as unverified. Make one reversible change, repeat the same check, and reject any fix that depends on guessing another board profile.
