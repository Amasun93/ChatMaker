---
schema_version: "1.0"
kind: knowledge-page
stable_id: arduino-nano-classic-libraries-and-examples
board_id: arduino-nano-classic
section_id: libraries-and-examples
source_refs:
  - source-arduino-nano-classic-documentation
---
# 常用库和起步示例

按用户想实现的效果选择一个最小示例，先调通单个模块，再组合功能。

- OLED：`DFRobot_SSD1306_I2C.h`，示例 `examples/chatduino/nano/oled-dashboard/oled-dashboard.ino`
- LCD1602 I2C：LiquidCrystal_PCF8574 2.3.0，示例 `examples/chatduino/nano/lcd1602-i2c-hello/lcd1602-i2c-hello.ino`
- WS2812：`DFRobot_NeoPixel.h`，示例 `examples/chatduino/nano/ws2812-one-pixel/ws2812-one-pixel.ino`
- SG90：`DFRobot_Servo.h`，示例 `examples/chatduino/nano/servo-button/servo-button.ino`
- HC-SR04：Arduino 内置脉冲 API，示例 `examples/chatduino/nano/ultrasonic-buzzer/ultrasonic-buzzer.ino`

常见排错顺序：先核对模块型号与引脚丝印，再看供电和共地，再扫描 I2C 地址，最后检查库和代码。编译成功不等于已经烧录或实物有效。
