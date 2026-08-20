---
schema_version: "1.0"
kind: knowledge-page
stable_id: arduino-uno-r3-troubleshooting
board_id: arduino-uno-r3
section_id: troubleshooting
source_refs:
  - source-arduino-uno-r3-documentation
---
# Find the earliest unsupported claim

Reload canonical `arduino-uno-r3`, every selected component ID, and the recipe ID. Identify the first failing or unproven gate among environment, identity, wiring, compile, upload, runtime, and physical effect. Check that gate without altering later statuses. Apply one reversible change, repeat the same observation, and report only what the new evidence demonstrates; never guess a similar board or port.

For a blank I2C OLED, disconnect power before checking VCC/GND/SCL/SDA, then use the read-only scanner in the ChatDuino OLED reference. No address points back to power or wiring; an address with no image points to address, controller, resolution or driver. If English works but Chinese does not, check the selected U8g2 font's glyph coverage and AVR memory instead of rewiring the display.
