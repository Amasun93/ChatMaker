---
schema_version: "1.0"
kind: llmwiki-page
stable_id: arduino-nano-classic-troubleshooting
board_id: arduino-nano-classic
section_id: troubleshooting
source_refs:
  - source-arduino-nano-classic-documentation
---
# Diagnose the first failed gate

Reload canonical `arduino-nano-classic`, the selected component IDs, and the recipe ID before changing anything. Locate the first unsupported gate: environment, identity, wiring, compile, upload, serial runtime, or physical effect. Inspect only evidence for that gate and preserve all later gates as unverified. Make one reversible change, rerun the same check, and report the observed result without upgrading unrelated status.
