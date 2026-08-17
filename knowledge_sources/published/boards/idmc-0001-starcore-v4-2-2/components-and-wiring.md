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

机械设计读取稳定机械资料，而不是从接线图量尺寸。星核板外框、四个定位中心、定位件和 USB-C 开口资料位于 `knowledge/mechanical/boards/idmc-0001-starcore-v4-2-2.json`。原始制造资料不公开；加工前需要真实板卡试装。
