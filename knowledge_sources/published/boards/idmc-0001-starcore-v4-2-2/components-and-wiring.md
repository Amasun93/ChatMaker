---
schema_version: "1.0"
kind: knowledge-page
stable_id: idmc-0001-starcore-v4-2-2-components-and-wiring
board_id: idmc-0001-starcore-v4-2-2
section_id: components-and-wiring
source_refs:
  - source-idmc-0001-starcore-v4-2-2-owned-docs
---
# 模块、接线和机械接口

先断电，再按模块编号和实物丝印接线。IDMD-0001 不是 WS2812，IDMS-0001 不是 I2C 彩灯按钮，IDMS-0009 也不是 I2C 超声波。下面是七个自研模块的课堂起点；更完整的电气限制以同名 Component 卡和 Recipe 为准。

```text
IDMD-0001 共阳 RGB 灯（低电平点亮）
VCC   -> 3V3
RED   -> P13
GREEN -> P14
BLUE  -> P15

IDMD-0002 串口 MP3
VCC -> 星核板明确标出的 5V 接口
GND -> GND
TXD -> P15（主控接收）
RXD -> P16（主控发送）

IDMD-0021 1.3 寸 OLED
VCC -> 3V3
GND -> GND
SCL -> P19
SDA -> P20

IDMS-0001 三线按钮（按下为 HIGH）
VCC -> 3V3
GND -> GND
SIG -> P8

IDMS-0003 电位器
VCC -> 3V3
GND -> GND
SIG -> P0

IDMS-0008 DHT11
VCC -> 3V3
GND -> GND
SIG -> P0

IDMS-0009 超声波（GPIO 路线）
VCC  -> 3V3
GND  -> GND
TRIG -> H（代码 P_H）
ECHO -> O（代码 P_O）
```

P0、P15 等引脚不能同时被两个模块占用。IDMD-0002 的 TXD/RXD 必须交叉连接；IDMS-0009 的 ECHO 实际电平尚未测量，接实体板前要先确认保护方式。普通 OLED、LCD1602、WS2812、SG90 和 HC-SR04 仍有通用 Component 卡，但不能代替上述自研编号卡。

机械设计读取稳定机械资料，而不是从接线图量尺寸。星核板外框、四个定位中心、定位件和 USB-C 开口资料位于 `knowledge/mechanical/boards/idmc-0001-starcore-v4-2-2.json`。原始制造资料不公开；加工前需要真实板卡试装。
