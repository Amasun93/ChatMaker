# 微雪 ESP32-S3-Touch-LCD-2.8

Exact board ID: `waveshare-esp32-s3-touch-lcd-2-8`. This is not DOIT ESP32 DevKit V1, and the separately named 2.8B/2.8C models are not aliases.

If the user supplies the exact product name and V2 / CST3530, select `--revision v2` for generation and compilation. A controller name on its own is a clue. Verify the physical target and port before upload.

## Classroom route

Save the complete program, then use the explicit checkout's `chatmaker-hardware --request-file project.json` (or `--request-json -` via stdin) with `board_id`, `revision`, and `sketch` (or complete `code`). To observe a marker via native USB, use `expected_serial_marker` and set `serial_probe` to the example's single-character query. After the physical board and revision have actually been confirmed, pass `board_confirmed:true` internally. Do not ask the student to fill technical JSON fields. With multiple native USB candidates, select the intended `port` explicitly.

`revision` must be `v1` (CST328) or `v2` (CST3530), determined by the back label or equivalent reliable evidence. Unknown revision remains unknown; the shared software can be prepared separately but do not upload a guessed touch variant. Reading an ESP32-S3 chip or a COM port does not prove the product model/revision.

The independent board CLI is `chatmaker-waveshare-s3` with `doctor`, `prepare-environment`, `ports`, `compile`, `compile-upload`. Use this route with the project's managed tools. For compilation on a new setup, preview pending downloads with `chatmaker-hardware --action prepare-environment --board-id waveshare-esp32-s3-touch-lcd-2-8 --revision v2 --dry-run`. If files are needed, name the component the tool reports. With `remaining_download_bytes: 0`, the downloaded archives are already present and verified, although first preparation may still unpack them. Reuse the same runtime root across projects. Use the board-specific preparation result for readiness.

On macOS use the source checkout's launcher prepared by `bash scripts/setup_local_runtime.sh`. The native USB serial address is a `/dev/cu.*` path. See `docs/verification/workbuddy-retest-macos.md` for setup and the USB retest.

Integrity covers the complete S3 compiler, core, SDK and relevant Arduino tools, plus all prepared drivers and recovery images. A ready receipt also requires configuration for the current local root. ESP32 core/compiler/SDK/flasher use identical hash-locked archives from the official domestic endpoint first. CLI and Arduino helper artifacts currently use official fallback addresses. With `CHATMAKER_DOWNLOAD_POLICY=domestic-only`, any missing component without a verified domestic source must stop explicitly; cached verified archives or a configured school HTTPS mirror can satisfy it. Rebuild isolated configuration at the destination root instead of treating a copied installation receipt as portable. See `docs/verification/workbuddy-retest-0.2.0-beta.5.md` for preview, provenance and test commands.

During repeated compilation of the same saved sketch, use a dedicated `--build-path`, optionally `--compile-timeout 1800` and `--jobs 2`. Use a new or empty path for the first build and reuse it for the same sketch and revision. On timeout, preserve the JSON and inspect actual compiler output and object file progress. On Windows, ChatMaker passes explicit GCC C++ standard-library and ESP32-S3 no-RTTI target include paths. If the path remains too deep, use a shorter local runtime root and a verified cache.

## Available examples

- `examples/chatduino/waveshare-s3/screen-diagnostic`: color screen status; marker `CHATMAKER_WAVESHARE_SCREEN_READY`.
- `examples/chatduino/waveshare-s3/classroom-timer`: 60-second START/PAUSE/RESET touch timer; marker `CHATMAKER_WAVESHARE_TIMER_READY`.
- `examples/chatduino/waveshare-s3/v2-tilt-dot`: V2-only direct ST7789 drawing and QMI8658 input. `D` requests a `TILT_DOT` summary with bus and recent frame measurements.
- `examples/chatduino/waveshare-s3/v2-salt-lake` (盐湖气象巡航): tilt the V2 board to bank and steer a layered pixel glider. Set the board level at startup. The screen shows FPS. Send `D` at 115200 baud for a `SALT_S3` summary with frame, drawing, and LCD transfer times. Send `C` while the board is level to recenter it.
- `examples/chatduino/waveshare-s3/v2-rift-runner` (裂星航线) uses the accelerometer and the speaker connector. Hold level at startup. Tilt to aim at either gate core for 0.6 seconds, then fly through the opening you created. The first exit selects the ice fjord or the furnace city. A quick sideways bank and return triggers a barrel roll through the scanner. At the fleet, level the board, then tilt sideways to replay. At 115200 baud, `D` reports game and device state, `M` reports timings by scene, and `F` returns a header and 160 × 120 little-endian RGB565 pixels. For repeatable bench measurements send `1` or `2` to supply scripted input, then `R` to restart with live input. Use `C` while level to recenter.

On one V2, both Rift Runner bench routes reached the fleet with two hits and two crossings. Impact close-ups averaged 34.77 and 35.03 FPS over 233 frames combined, with a 30 ms 95th-percentile frame time on both routes. Tunnel shots averaged 37.77 and 37.89 FPS over 252 frames combined. These measurements cover drawing, the 2× upscale and the 320 × 240 LCD transfer. Bench mode substitutes tilt input while the board continues sampling its IMU and driving its display and audio.

The screen and timer print one startup marker, and reply to `?` after a serial observer opens. For real-time interaction record timing in RAM and report it on demand. Host backpressure can stall hardware CDC writes even with a USB connection. Observe the device with no serial reader before querying, then check the actual screen, touch and power-cycle separately.

The prepared Waveshare ST7789 driver configures little-endian RGB565 through RAMCTRL. For a `uint16_t` buffer passed to `LCD_addWindow`, use native RGB565 values such as `0xF800` for red. When changing display orientation, check tilt directions against the physical screen edges.

## Fixed technical configuration

Managed Arduino CLI 1.6.0 or 1.3.1, official Arduino-ESP32 3.3.11, target `esp32:esp32:esp32s3`, 16 MB flash, 8 MB OPI PSRAM, QIO flash, `app3M_fat9M_16MB` partition, hardware CDC/JTAG with CDC enabled at boot. Verify compilation evidence before describing this as tested on hardware.

Vendor LVGL 8.3.10 and display/touch sources are downloaded from the official revision-specific ZIP and checked by size/SHA-256. The V2 archive supplies CST3530 but its display/LVGL callbacks still invoke CST328. The managed preparation explicitly selects `TOUCH2_Init`, `Touch2_Read_Data`, `Touch2_Get_XY` and the CST3530 point-count definition. Changes are made to locally prepared files; the official archive is retained unchanged.

The V2 managed package also extracts QMI8658 and its board I²C helper as `WaveshareMotion`. Check `peripheral_coverage` and `ready_for_compile` first. `ESP_I2S.h` comes from the ESP32 core, with PCM5101 BCLK48/WS38/DOUT47 for this model. The vendor's audio/SD stack and full LVGL example require separate dependencies. Do not infer actual sound, initialization, or real-time smoothness from compilation or a successful serial command. Issue #6 reports whole-region composition as a verified baseline for its v6.4 firmware. The cause of local erase trails remains unknown. See `docs/verification/2026-11-19-waveshare-issue-6.md`.

GPIO layout: display MOSI45/SCLK40/CS42/DC41/RST39/backlight5; touch SDA1/SCL3/RST2/INT4; external shared I2C SDA11/SCL10; free extension GPIO15/18; UART43/44. GPIO19/20 are native USB and remain reserved during this classroom route. GPIO logic is 3.3 V. Board power hold is GPIO7; examples set it high.

Official resources include factory test firmware for recovery. Preparation keeps those images and hashes in its local revision cache; this is not a backup of a student's current custom firmware. A requested new program overwrites firmware; do not write when the user only asked to discuss or inspect a board.

## Knowledge and evidence

The installed ChatMaker Skill contains this reference. A full ChatMaker checkout also provides the eight Wiki sections under `knowledge_sources/published/boards/waveshare-esp32-s3-touch-lcd-2-8/`. Use `chatmaker-knowledge` with the exact board ID and `auto_install:false` for one section. If the full checkout is unavailable, use the bundled reference for board questions. Mechanical fit and CAD hole placement remain research-required.

Sources:
- https://docs.waveshare.net/ESP32-S3-Touch-LCD-2.8/
- https://docs.waveshare.net/ESP32-S3-Touch-LCD-2.8/Resources-And-Documents/
- https://docs.waveshare.net/ESP32-S3-Touch-LCD-2.8/Arduino/

See `docs/verification/2026-11-10-waveshare-s3-independent-flow.md` for the actual evidence reached; never upgrade an untested physical gate.
