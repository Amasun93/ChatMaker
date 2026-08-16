---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-devkit-v1-toolchains-and-upload
board_id: esp32-devkit-v1
section_id: toolchains-and-upload
source_refs:
  - source-esp32-devkit-v1-doit-board-definition
---
# Use the currently supported target

Load the current toolchain identity and status directly from canonical `esp32-devkit-v1`; do not rely on a command copied into prose. Confirm carrier identity and the wired port before any action. Record environment readiness, compilation, upload, reboot, runtime logs, network behavior, and physical effect separately. An unavailable toolchain must remain a blocker rather than being silently replaced by a similar target.
