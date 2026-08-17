---
schema_version: "1.0"
kind: knowledge-page
stable_id: arduino-uno-r3-components-and-wiring
board_id: arduino-uno-r3
section_id: components-and-wiring
source_refs:
  - source-arduino-uno-r3-documentation
---
# 常用模块接线

Uno R3 与经典 Nano 同为 5V ATmega328P，下面使用相同的课堂起步引脚。

```text
OLED 或 LCD1602 I2C
VCC -> 5V（OLED 要先确认模块支持）
GND -> GND
SDA -> A4
SCL -> A5
LCD1602 先扫描地址，0x27 不是固定值

WS2812
5V  -> 外部 5V 电源
GND -> 外部电源 GND，并与 Uno GND 共地
DIN -> D6（串联 300~500Ω 电阻）

SG90
正极 -> 外部 5V 电源
GND  -> 外部电源 GND，并与 Uno GND 共地
信号 -> D9

HC-SR04
VCC -> 5V   GND -> GND
TRIG -> D7  ECHO -> D8
```

使用五张共享组件卡读取型号限制、供电规则和常见错误。不要仅凭“一个屏幕”就猜驱动芯片或接口。
