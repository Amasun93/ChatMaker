---
schema_version: "1.0"
kind: knowledge-page
stable_id: arduino-nano-classic-components-and-wiring
board_id: arduino-nano-classic
section_id: components-and-wiring
source_refs:
  - source-arduino-nano-classic-documentation
---
# 常用模块接线

先确认板卡是 5V 逻辑的经典 Nano，再读取对应组件卡。给初学者时一次只讲一根线；模块型号或丝印不一致就先停下确认。

```text
0.96寸 SSD1306 I2C OLED
VCC -> 5V（先确认模块支持 5V）
GND -> GND
SDA -> A4
SCL -> A5

LCD1602 + PCF8574 I2C 背包
VCC -> 5V
GND -> GND
SDA -> A4
SCL -> A5
先扫描地址，0x27 只是常见值

WS2812 单灯/灯带
5V  -> 合适的外部 5V 电源
GND -> 外部电源 GND，并与 Nano GND 共地
DIN -> D6（串联 300~500Ω 电阻）

SG90 舵机
红线/正极 -> 外部 5V 电源
棕线/黑线 -> 外部电源 GND，并与 Nano GND 共地
信号线 -> D9

HC-SR04
VCC  -> 5V
GND  -> GND
TRIG -> D7
ECHO -> D8
```

使用组件卡：`ssd1306-i2c-128x64-module`、`lcd1602-i2c-pcf8574`、`ws2812b-addressable-rgb`、`sg90-micro-servo`、`hc-sr04`。不要从 GPIO 给灯带或舵机供电。
