# 微雪 ESP32-S3-Touch-LCD-2.8

Exact board ID: `waveshare-esp32-s3-touch-lcd-2-8`. This is not DOIT ESP32 DevKit V1, and the separately named 2.8B/2.8C models are not aliases.

## Classroom route

Save the complete program, then use the explicit checkout's `chatmaker-hardware --request-file project.json` (or `--request-json -` via stdin) with `board_id`, `revision`, `sketch` (or complete `code`), and `expected_serial_marker`. After the physical board and revision have actually been confirmed, pass `board_confirmed:true` internally. Do not ask the student to fill technical JSON fields. With multiple native USB candidates, select the intended `port` explicitly.

`revision` must be `v1` (CST328) or `v2` (CST3530), determined by the back label or equivalent reliable evidence. Unknown revision remains unknown; the shared software can be prepared separately but do not upload a guessed touch variant. Reading an ESP32-S3 chip or a COM port does not prove the product model/revision.

The independent board CLI is `chatmaker-waveshare-s3` with `doctor`, `prepare-environment`, `ports`, `compile`, `compile-upload`. Missing Mind+ does not block this route. First preparation installs required tools into the managed runtime; subsequent projects reuse the verified cache. The general local check is not a board-specific readiness decision.

On macOS use the source checkout's launcher prepared by `bash scripts/setup_local_runtime.sh`. The native USB serial address is a `/dev/cu.*` path. See `docs/verification/workbuddy-retest-macos.md` for setup and the USB retest.

Integrity covers the complete S3 compiler, core, SDK and relevant Arduino tools, plus all prepared drivers and recovery images. A ready receipt also requires configuration for the current local root. ESP32 core/compiler/SDK/flasher use identical hash-locked archives from the official domestic endpoint first. CLI and Arduino helper artifacts currently use official fallback addresses. With `CHATMAKER_DOWNLOAD_POLICY=domestic-only`, any missing component without a verified domestic source must stop explicitly; cached verified archives or a configured school HTTPS mirror can satisfy it. Rebuild isolated configuration at the destination root instead of treating a copied installation receipt as portable. See `docs/verification/workbuddy-retest-0.2.0-beta.5.md` for preview, provenance and test commands.

## Available examples

- `examples/chatduino/waveshare-s3/screen-diagnostic`: color screen status; marker `CHATMAKER_WAVESHARE_SCREEN_READY`.
- `examples/chatduino/waveshare-s3/classroom-timer`: 60-second START/PAUSE/RESET touch timer; marker `CHATMAKER_WAVESHARE_TIMER_READY` and event logs. The initial controls use clear English labels to avoid claiming a complete Chinese font solution.

Both repeat their startup/status markers every two seconds so a serial observer opened after USB reset can still verify execution. Observe the real screen/touch and power-cycle separately; log messages alone cannot prove the visible effect.

## Fixed technical configuration

Managed Arduino CLI 1.6.0 or 1.3.1, official Arduino-ESP32 3.3.11, target `esp32:esp32:esp32s3`, 16 MB flash, 8 MB OPI PSRAM, QIO flash, `app3M_fat9M_16MB` partition, hardware CDC/JTAG with CDC enabled at boot. Verify compilation evidence before describing this as tested on hardware.

Vendor LVGL 8.3.10 and display/touch sources are downloaded from the official revision-specific ZIP and checked by size/SHA-256. The V2 archive supplies CST3530 but its display/LVGL callbacks still invoke CST328. The managed preparation explicitly selects `TOUCH2_Init`, `Touch2_Read_Data`, `Touch2_Get_XY` and the CST3530 point-count definition. Changes are made to locally prepared files; the official archive is retained unchanged.

GPIO layout: display MOSI45/SCLK40/CS42/DC41/RST39/backlight5; touch SDA1/SCL3/RST2/INT4; external shared I2C SDA11/SCL10; free extension GPIO15/18; UART43/44. GPIO19/20 are native USB and remain reserved during this classroom route. GPIO logic is 3.3 V. Board power hold is GPIO7; examples set it high.

Official resources include factory test firmware for recovery. Preparation keeps those images and hashes in its local revision cache; this is not a backup of a student's current custom firmware. A requested new program overwrites firmware; do not write when the user only asked to discuss or inspect a board.

## Knowledge and evidence

This source reference and the canonical board record are available locally. A signed downloadable Knowledge package has not been published; use this reference instead of requesting a nonexistent pack. Mechanical fit and CAD hole placement remain research-required.

Sources:
- https://docs.waveshare.net/ESP32-S3-Touch-LCD-2.8/
- https://docs.waveshare.net/ESP32-S3-Touch-LCD-2.8/Resources-And-Documents/
- https://docs.waveshare.net/ESP32-S3-Touch-LCD-2.8/Arduino/

See `docs/verification/2026-11-10-waveshare-s3-independent-flow.md` for the actual evidence reached; never upgrade an untested physical gate.
