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

OLED 黑屏先运行 ChatDuino OLED 参考卡里的只读扫描程序，确认 A4(SDA)、A5(SCL) 和真实地址，再检查控制器与驱动。需要中文时可以使用 U8g2 页面缓冲和目标文字的字体子集；不要默认完整中文字库能够放进 Uno，必须编译准确程序检查 Flash/RAM 和缺字情况。

先跑一个模块的最小示例。显示屏空白优先检查型号、地址和对比度；舵机抖动或板卡重启优先检查独立供电与共地；超声波超时不能当作 0 cm。
