---
schema_version: "1.0"
kind: knowledge-page
stable_id: stardust-atmega328p-pins-and-electrical
board_id: stardust-atmega328p
section_id: pins-and-electrical
source_refs: [source-stardust-atmega328p-observed]
---
# 只使用已有证据的针脚

当前代表组合只确认 5V、GND、A4（I²C SDA）和 A5（I²C SCL）。连接的 IDMD-0021 OLED 在 0x3C 应答。其余数字、模拟、串口和板载功能必须等待星辰板原理图、针脚表或逐项实测。

上传期间保持 D0/D1 空闲。地址应答不能证明屏幕肉眼可见。
