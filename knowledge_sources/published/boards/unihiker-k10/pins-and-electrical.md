---
schema_version: '1.0'
kind: knowledge-page
stable_id: unihiker-k10-pins-and-electrical
board_id: unihiker-k10
section_id: pins-and-electrical
source_refs:
- source-unihiker-k10-official
---
# DFRobot UNIHIKER K10 行空板｜引脚和电气规则

4 针 Gravity I²C 的数据是 P20/SDA，时钟是 P19/SCL，对应核心的 GPIO47/48。板上也有设备使用该总线。两个 3 针 Gravity 接口看 P0、P1 丝印。信号为 3.3 V，USB 的 5 V 是供电规格。

[K10 引脚图和原理图](https://www.unihiker.com.cn/wiki/k10/jianjie) · [K10 Arduino 引脚定义](https://github.com/DFRobot/framework-arduinounihiker/blob/master/variants/unihiker_k10/pins_arduino.h)
