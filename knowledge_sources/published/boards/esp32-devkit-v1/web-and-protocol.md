---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-devkit-v1-web-and-protocol
board_id: esp32-devkit-v1
section_id: web-and-protocol
source_refs:
  - source-esp32-devkit-v1-doit-board-definition
---
# Use the existing AP and HTTP recipe

For canonical board `esp32-devkit-v1`, load only canonical recipe `esp32-ap-led-sensor` for the current access-point and HTTP workflow. Follow its message behavior, component IDs, and board references instead of restating them here. Its runtime gates remain unverified until separately observed: firmware upload, network availability, protocol exchange, and physical effect cannot be inferred from source review, page rendering, or compilation.
