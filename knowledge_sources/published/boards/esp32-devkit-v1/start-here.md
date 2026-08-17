---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-devkit-v1-start-here
board_id: esp32-devkit-v1
section_id: start-here
source_refs:
  - source-esp32-devkit-v1-doit-board-definition
---
# Start from carrier-board identity

Load canonical board `esp32-devkit-v1` before choosing pins, tools, networking, or code. Ask the learner to confirm the carrier board using the identity guidance in that record. Select only a canonical recipe that names this board. Keep compilation, upload, network availability, protocol exchange, and physical effect as separate gates, and open a more detailed section only when its topic is required.

For CAD work, use `knowledge/mechanical/boards/esp32-devkit-v1.json`. This 30-pin profile is a community reference because DOIT-style clones vary and do not share standard mounting holes. Use a cradle or clips and measure the user's actual carrier before designing a tight enclosure.
