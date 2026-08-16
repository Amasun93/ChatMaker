---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-devkit-v1-components-and-wiring
board_id: esp32-devkit-v1
section_id: components-and-wiring
source_refs:
  - source-esp32-devkit-v1-doit-board-definition
---
# Resolve shared component facts once

Begin with canonical board `esp32-devkit-v1`, then load each component by its canonical ID and select a canonical recipe for the intended relationship. The component record owns interface and safety facts; the board owns pin constraints; the recipe owns the connection plan. Guide one reversible step at a time, naming the observation expected next, and pause whenever the actual module variant is uncertain.
