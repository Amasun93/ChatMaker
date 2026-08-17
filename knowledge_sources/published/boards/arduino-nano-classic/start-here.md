---
schema_version: "1.0"
kind: knowledge-page
stable_id: arduino-nano-classic-start-here
board_id: arduino-nano-classic
section_id: start-here
source_refs:
  - source-arduino-nano-classic-documentation
---
# Start with the exact board

Load the canonical board record `arduino-nano-classic` before proposing code, wiring, or tools. Ask the learner to confirm the physical board, then choose one canonical recipe ID that matches the intended effect. Treat environment discovery, compilation, upload, runtime observation, and physical confirmation as separate results. Continue to a narrower section only when its topic is needed.

For CAD work, use the normalized profile `knowledge/mechanical/boards/arduino-nano-classic.json`. The official PCB holes are small, so choose a header cradle or confirm the intended fastener before printing. Generated geometry remains physically unverified until it is tried with the actual board.
