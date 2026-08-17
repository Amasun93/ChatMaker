---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-devkit-v1-components-and-wiring
board_id: esp32-devkit-v1
section_id: components-and-wiring
source_refs:
  - source-esp32-devkit-v1-doit-board-definition
---
# 常用模块接线

只适用于已确认的 DOIT ESP32 DEVKIT V1。ESP32 GPIO 是 3.3V，任何 5V 返回信号都不能直接接入。

```text
SSD1306 I2C OLED（确认模块可在 3.3V 工作）
VCC -> 3V3   GND -> GND
SDA -> GPIO21
SCL -> GPIO22

LCD1602 + PCF8574
VCC/GND -> 按模块要求供电
SDA -> GPIO21，SCL -> GPIO22
普通 5V 背包应加双向 I2C 电平转换，再扫描地址

WS2812
5V  -> 外部 5V 电源
GND -> 外部电源 GND，并与 ESP32 GND 共地
DIN -> GPIO27，可靠课堂接法增加 3.3V→5V 电平转换

SG90
正极/GND -> 外部 5V 电源，并与 ESP32 共地
信号 -> GPIO18

HC-SR04
VCC -> 5V   GND -> GND
TRIG -> GPIO25
ECHO -> 分压或电平转换 -> GPIO26
```

不要使用 GPIO34 驱动输出；不要让 ECHO 或 I2C 上拉把 5V 送入 ESP32。
