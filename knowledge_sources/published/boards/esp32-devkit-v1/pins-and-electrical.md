---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-devkit-v1-pins-and-electrical
board_id: esp32-devkit-v1
section_id: pins-and-electrical
source_refs:
  - source-esp32-devkit-v1-doit-board-definition
---
# Resolve every pin at use time

Read pin capabilities, electrical facts, startup constraints, and reserved resources from canonical board `esp32-devkit-v1`. Combine those facts with the canonical component record and selected recipe ID. Confirm any unclear board label before applying the profile. If the learner used a different pin from the recipe, check that pin for the actual project and keep it when it is safe and compatible.
