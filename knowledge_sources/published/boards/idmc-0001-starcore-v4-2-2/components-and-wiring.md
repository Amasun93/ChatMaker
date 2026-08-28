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

板载 A/B 按键、无源蜂鸣器和 QMI8658 已经连接到 P5、P11、P6 与共享 I2C，不需要再接一个外部模块。若用户只要按键、提示音或体感控制，优先使用这些板载器件；但仍要在引脚占用表中保留它们。掌控板软件中的 `display/rgb/light/sound` 不属于星核板板载器件，需要按具体外接模块另行接线。

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

IDMD-0021 1.3 寸 OLED（I2C 四芯线，整条插入一个匹配电压的 I2C 接口）
VCC -> 模块额定电压对应的 3V3 或 5V 插口
GND -> 同一插口的 GND
SCL -> 同一插口的 SCL/C（与 SDA 相邻）
SDA -> 同一插口的 SDA/D（与 SCL 相邻）

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

IDMS-0009 超声波（GPIO 路线，四芯线中的 2 根电源线 + 2 根信号线）
红 VCC  -> 3V3（先按当前批次丝印确认）
黑 GND  -> GND
蓝 TRIG -> H/P26（代码 P_H）
绿 ECHO -> O/P27（代码 P_O）
```

P0、P15 等引脚不能同时被两个模块占用。IDMD-0002 的 TXD/RXD 必须交叉连接；IDMS-0009 的 ECHO 实际电平尚未测量，接实体板前要先确认保护方式。IDMS-0009 的 H/O 两根信号线不能被误接到 I2C 的 SCL/SDA；反过来，I2C 模块的 SCL/SDA 也不能拆到两个相距很远的 GPIO 插口。普通 OLED、LCD1602、WS2812、SG90 和 HC-SR04 仍有通用 Component 卡，但不能代替上述自研编号卡。

外接 OLED 若使用 `MPython.h` 的全局 `display`，通常占用共享 I2C 地址 `0x3C`；它和板载 QMI8658 的 `0x6B` 可以共线，但仍要检查其他 I2C 模块地址。P13/P14 已接板载 CAN 收发器，不作为外接 RGB、舵机或普通数字模块的默认起点。

课堂常用的 WS2812 和 SG90 保持为通用组件，不另造“星核版”组件卡：

```text
WS2812 三线灯带
DIN -> P8（可靠课堂方案先经 74AHCT125 3.3V→5V 电平转换和 330Ω）
5V -> 独立足量 5V 电源
GND -> 外部电源 GND 与星核板 GND 共地

SG90 普通三线 PWM 舵机
SIGNAL -> P9
V+ -> 独立足量 5V 电源
GND -> 外部电源 GND 与星核板 GND 共地
```

WS2812 要确认 DIN 方向，按约 60mA/灯珠最坏值并留余量选电源；不能从 GPIO 或 3V3 供电。SG90 上电前清空机构周围，第一次只测试 60/90/120 度小范围。

IDMM-0007 是串口舵机驱动，不是 SG90 三线 PWM 接口。协议不明时只做接收诊断：模块 TXD 接 P26、GND 共地，模块 RXD/P23 暂不连接；供电范围和 UART 电平未确认前不要通电。不得复制其他品牌协议发送试转、复位或扫描 ID 命令。

机械设计读取稳定机械资料，而不是从接线图量尺寸。星核板外框、四个定位中心、定位件和 USB-C 开口资料位于 `knowledge/mechanical/boards/idmc-0001-starcore-v4-2-2.json`。原始制造资料不公开；加工前需要真实板卡试装。
