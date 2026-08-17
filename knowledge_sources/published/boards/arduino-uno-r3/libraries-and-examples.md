---
schema_version: "1.0"
kind: knowledge-page
stable_id: arduino-uno-r3-libraries-and-examples
board_id: arduino-uno-r3
section_id: libraries-and-examples
source_refs:
  - source-arduino-uno-r3-documentation
---
# 常用库和起步示例

- OLED：`DFRobot_SSD1306_I2C.h`，示例 `examples/chatduino/uno/oled-dashboard/oled-dashboard.ino`
- LCD1602 I2C：LiquidCrystal_PCF8574 2.3.0，示例 `examples/chatduino/uno/lcd1602-i2c-hello/lcd1602-i2c-hello.ino`
- WS2812：`DFRobot_NeoPixel.h`，示例 `examples/chatduino/uno/ws2812-one-pixel/ws2812-one-pixel.ino`
- SG90：`DFRobot_Servo.h`，示例 `examples/chatduino/uno/servo-button/servo-button.ino`
- HC-SR04：Arduino 内置脉冲 API，示例 `examples/chatduino/uno/ultrasonic-distance/ultrasonic-distance.ino`

先跑一个模块的最小示例。显示屏空白优先检查型号、地址和对比度；舵机抖动或板卡重启优先检查独立供电与共地；超声波超时不能当作 0 cm。
