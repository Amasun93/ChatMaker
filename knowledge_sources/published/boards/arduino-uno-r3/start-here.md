---
schema_version: "1.0"
kind: knowledge-page
stable_id: arduino-uno-r3-start-here
board_id: arduino-uno-r3
section_id: start-here
source_refs:
  - source-arduino-uno-r3-documentation
---
# Start with the exact board

Load canonical board `arduino-uno-r3` before offering a circuit, program, or tool command. Confirm that the learner's board identity matches that record, then select a canonical recipe ID for the desired effect. Keep environment, compilation, upload, runtime observation, and physical confirmation as separate evidence. Use the remaining sections only when the current task needs their narrower guidance.

For CAD work, use `knowledge/mechanical/boards/arduino-uno-r3.json`, normalized from Arduino's official board CAD. Connector envelopes are still pending, so leave practical clearance around USB and power connectors and keep physical fit unverified until a real-board trial.
