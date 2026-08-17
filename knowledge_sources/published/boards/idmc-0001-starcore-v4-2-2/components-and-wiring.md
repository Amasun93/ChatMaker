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

模块必须按自研编号和实物丝印识别，不能只按“一个 OLED”或“一个超声波”匹配通用资料。已清洗的课堂模式包括：IDMD-0002 串口 MP3、IDMD-0021 OLED、IDMS-0008 DHT11、IDMS-0009 超声波，以及普通 WS2812 灯带和舵机。

常用起点：DHT11 使用 3.3V、GND、SIG→P0；IDMD-0021 OLED 整体插入匹配电压的空闲 I2C 接口；串口 MP3 的模块 TXD→主控 P15、模块 RXD→主控 P16；超声波资料使用 TRIG→H、ECHO→O，代码中写 `P_H`、`P_O`。这些起点仍要按当前模块批次复核供电和信号电平。

五类常用显示与交互模块的简单接法：

```text
IDMD-0021 OLED
整体插入匹配电压的 I2C 接口；总线使用共享的 P19/P20

LCD1602 + PCF8574
接匹配电压的 I2C 接口；普通 5V 背包需双向电平转换
先扫描地址，示例中的 0x27 不是固定值

WS2812 灯带
DIN -> P8
5V  -> 外部 5V 电源；灯带、电源和星核板 GND 共地
课堂可靠接法增加 3.3V→5V 数据电平转换

SG90 舵机
信号 -> P9
正极/GND -> 外部 5V 电源，并与星核板共地

IDMS-0009 超声波（普通 HC-SR04 需另按实物确认引脚与电平）
TRIG -> 丝印 H（代码 P_H）
ECHO -> 丝印 O（代码 P_O）
ECHO 电平不明确时先做 3.3V 保护
```

机械设计读取稳定机械资料，而不是从接线图量尺寸。星核板外框、四个定位中心、定位件和 USB-C 开口资料位于 `knowledge/mechanical/boards/idmc-0001-starcore-v4-2-2.json`。原始制造资料不公开；加工前需要真实板卡试装。
