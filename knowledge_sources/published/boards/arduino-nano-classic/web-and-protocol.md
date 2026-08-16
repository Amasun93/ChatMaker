---
schema_version: "1.0"
kind: llmwiki-page
stable_id: arduino-nano-classic-web-and-protocol
board_id: arduino-nano-classic
section_id: web-and-protocol
source_refs:
  - source-arduino-nano-classic-documentation
---
# Plan the communication route first

Canonical board `arduino-nano-classic` does not have native Wi-Fi and therefore needs a host or an extra communication route for a web experience. Define the message contract before generating hardware or page code. Load canonical records for the chosen communication component and recipe, keep browser rendering separate from hardware runtime evidence, and never imply that a local page proves a physical effect.
