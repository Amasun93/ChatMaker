---
schema_version: '1.0'
kind: knowledge-page
stable_id: arduino-uno-r4-wifi-pins-and-electrical
board_id: arduino-uno-r4-wifi
section_id: pins-and-electrical
source_refs:
- source-arduino-uno-r4-wifi-official
---
# Arduino UNO R4 WiFi｜引脚和电气规则

常见排针信号是 5 V。主 I²C 用 `Wire`，A4/SDA、A5/SCL 与上边独立标出的 SDA/SCL 各自相连。Qwiic 是另一条 3.3 V 总线，用 `Wire1`。D13 与 SPI 时钟共享，D0/D1 留给需要 `Serial1` 的项目。

[Arduino 完整引脚图](https://docs.arduino.cc/resources/pinouts/ABX00087-full-pinout.pdf) · [Arduino 两条 I²C 的定义](https://github.com/arduino/ArduinoCore-renesas/tree/1.6.0/variants/UNOWIFIR4)
