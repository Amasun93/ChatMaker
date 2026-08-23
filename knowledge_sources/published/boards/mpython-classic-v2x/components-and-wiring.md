---
schema_version: "1.0"
kind: knowledge-page
stable_id: mpython-classic-v2x-components-and-wiring
board_id: mpython-classic-v2x
section_id: components-and-wiring
source_refs: [source-mpython-classic-v2x-official]
---
# 先用板载器件

经典掌控板已带 OLED、三颗 RGB、光线、麦克风、无源蜂鸣器、A/B 键和六个触摸键。体感和磁场芯片随修订版本变化。AI 应先使用这些真实板载能力，避免让小白重复购买或连接同类模块。

外接模块时同时检查模块电压、信号电平、接口和占用引脚。大电流灯带、电机、舵机和泵不能从 GPIO 取电；使用独立电源并共地。

