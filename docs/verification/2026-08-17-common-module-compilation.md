# Common display and interaction module compilation

Date: 2026-08-17

Scope: source-level compilation only. No board was connected, so upload, serial output and physical effects remain unverified.

Results:

- Nano LCD1602 and Uno LCD1602 compiled with `arduino:avr@1.8.6` and `LiquidCrystal_PCF8574@2.3.0`. The existing Nano/Uno OLED, WS2812, servo and ultrasonic compilation evidence remains referenced by their component cards.
- ESP32 OLED, LCD1602, WS2812, servo and ultrasonic examples compiled with `esp32:esp32@3.3.11` and FQBN `esp32:esp32:esp32doit-devkit-v1`.
- ESP32 external libraries were `Adafruit SSD1306@2.5.17`, `Adafruit NeoPixel@1.15.5`, `ESP32Servo@3.2.1`, and `LiquidCrystal_PCF8574@2.3.0`; the SSD1306 dependency resolver installed the required Adafruit GFX dependency.
- Starcore OLED, LCD1602, WS2812, servo and ultrasonic examples compiled with the current Mind+ 1.8 target `dfrobot:mpython:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none`.

Two generated-code defects were found and fixed during the focused run: the Starcore LiquidCrystal wrapper requires coordinate arguments for text output, and `MPython.h` already defines a global named `pixels`, so the example's NeoPixel instance must use another name.
