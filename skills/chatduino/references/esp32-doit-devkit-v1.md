# DOIT ESP32 DEVKIT V1 / ESP-WROOM-32 safety contract

## Confirm the physical identity

Accept the profile only when the carrier board is confirmed as `DOIT ESP32 DEVKIT V1` and the radio module is confirmed as `ESP-WROOM-32`. Seeing only `ESP-WROOM-32` means the module is known but the carrier board is unresolved.

Do not treat these as aliases: `ESP32 Dev Module`, Espressif `ESP32-DevKitC`, FireBeetle, mPython, ESP32-C3, ESP32-S2, or ESP32-S3.

## Exact toolchain

```text
Core: esp32:esp32 3.3.11
Board ID: esp32doit-devkit-v1
FQBN: esp32:esp32:esp32doit-devkit-v1
```

The installed Mind+ `mindplus:esp32 0.0.1` package exposes only board-specific DFRobot and teaching variants. It is not a compatible fallback. Do not install or switch cores without explicit user authorization.

## Pin and voltage boundaries

- GPIO logic is 3.3 V. Never feed a 5 V signal directly into a GPIO.
- GPIO34-39 are input-only and lack software pull-up/pull-down support.
- GPIO0, GPIO2, GPIO5, GPIO12, and GPIO15 are strapping pins sampled during boot.
- GPIO6-11 are connected to flash and unavailable to ordinary projects.
- Reserve GPIO1 and GPIO3 for download and serial logs by default.
- ADC2 analog reads conflict with active Wi-Fi.
- GPIO16/17 are allowed only after confirming the module is WROOM or SOLO rather than WROVER.

For a beginner AP demonstration, prefer a current-limited external LED on GPIO23 and a 10 kOhm potentiometer powered from 3V3 with its wiper on GPIO34. Keep power disconnected while wiring and share GND.

## Evidence boundaries

An exact core and FQBN can prove compilation without hardware. They cannot prove upload, boot, serial output, Wi-Fi AP availability, HTTP requests, LED changes, sensor readings, or power-cycle recovery.
