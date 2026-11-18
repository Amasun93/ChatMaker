---
schema_version: '1.0'
kind: knowledge-page
stable_id: seeed-xiao-esp32s3-components-and-wiring
board_id: seeed-xiao-esp32s3
section_id: components-and-wiring
source_refs:
- source-seeed-xiao-esp32s3-official
---
# Seeed Studio XIAO ESP32S3｜板载器件和接线

第一次只插 USB。加 3.3 V I²C 传感器时接 VCC → 3V3、GND → GND、SDA → D4、SCL → D5。外接小灯可选 D1 串 1 kΩ 电阻。已经接过的普通 GPIO 可以保留，先确认程序使用了正确的 D 编号、电压和启动状态。

[Seeed 引脚对照表](https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/)
