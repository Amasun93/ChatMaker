---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-devkit-v1-libraries-and-examples
board_id: esp32-devkit-v1
section_id: libraries-and-examples
source_refs:
  - source-esp32-devkit-v1-doit-board-definition
---
# 常用库和起步示例

目标工具链为 `esp32:esp32@3.3.11` 和 `esp32:esp32:esp32doit-devkit-v1`。

- OLED：Adafruit SSD1306 2.5.17 + Adafruit GFX，示例 `examples/chatduino/esp32/oled-i2c-hello/oled-i2c-hello.ino`
- LCD1602 I2C：LiquidCrystal_PCF8574 2.3.0，示例 `examples/chatduino/esp32/lcd1602-i2c-hello/lcd1602-i2c-hello.ino`
- WS2812：Adafruit NeoPixel 1.15.5，示例 `examples/chatduino/esp32/ws2812-one-pixel/ws2812-one-pixel.ino`
- SG90：ESP32Servo 3.2.1，示例 `examples/chatduino/esp32/servo-button/servo-button.ino`
- HC-SR04：Arduino-ESP32 内置脉冲 API，示例 `examples/chatduino/esp32/ultrasonic-distance/ultrasonic-distance.ino`

一次只编译和接入一个模块；用户需要网页交互时，再进入 ChatWeb 增加串口或网络控制，不把前端强加给每个硬件项目。
