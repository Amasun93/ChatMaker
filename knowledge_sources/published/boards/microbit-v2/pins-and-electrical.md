---
schema_version: "1.0"
kind: knowledge-page
stable_id: microbit-v2-pins-and-electrical
board_id: microbit-v2
section_id: pins-and-electrical
source_refs: [source-microbit-v2-official]
---
# 按 V2 的 3.3V 规则接线

P0、P1、P2 可用于常见数字、模拟、PWM 和触摸输入；P19/P20 是常用 I²C 时钟和数据引脚。外接模块需要共地，并按 3.3V 逻辑设计，不要把 5V 信号直接送入板卡引脚。

V2 的板载 LED、按键、麦克风、扬声器等功能可能占用内部资源。做外接项目时应查官方 V2 引脚资料，不能照搬 V1 或其他开发板接线图。
