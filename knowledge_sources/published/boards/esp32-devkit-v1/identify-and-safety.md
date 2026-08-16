---
schema_version: "1.0"
kind: llmwiki-page
stable_id: esp32-devkit-v1-identify-and-safety
board_id: esp32-devkit-v1
section_id: identify-and-safety
source_refs:
  - source-esp32-devkit-v1-doit-board-definition
---
# Confirm the carrier, not merely the module

Use the canonical identity, forbidden aliases, constraints, sources, and verification fields in `esp32-devkit-v1`. Ask for visible board labels and layout evidence before compile or upload. Load canonical component and recipe records before wiring. If the carrier cannot be confirmed, remain blocked and explain what observation is missing instead of treating a module label or similar board name as proof.
