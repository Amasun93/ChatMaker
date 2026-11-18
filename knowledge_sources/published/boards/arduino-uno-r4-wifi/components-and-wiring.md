---
schema_version: '1.0'
kind: knowledge-page
stable_id: arduino-uno-r4-wifi-components-and-wiring
board_id: arduino-uno-r4-wifi
section_id: components-and-wiring
source_refs:
- source-arduino-uno-r4-wifi-official
---
# Arduino UNO R4 WiFi｜板载器件和接线

点阵小例子只插 USB。外接 LED 时，D2 → 1 kΩ 电阻 → LED 长脚，短脚 → GND。只支持 3.3 V 的 I²C 模块优先接板上的 Qwiic，程序用 `Wire1`。

已经接好时先检查模块规格和总线。A4/A5 上的 5 V 兼容模块可以保留。发现 3.3 V-only 模块被接到 5 V 电源或受 5 V 上拉的信号，先断电并改接。

[Arduino 完整引脚图](https://docs.arduino.cc/resources/pinouts/ABX00087-full-pinout.pdf)
