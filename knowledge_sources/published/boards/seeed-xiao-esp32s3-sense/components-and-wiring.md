---
schema_version: '1.0'
kind: knowledge-page
stable_id: seeed-xiao-esp32s3-sense-components-and-wiring
board_id: seeed-xiao-esp32s3-sense
section_id: components-and-wiring
source_refs:
- source-seeed-xiao-esp32s3-sense-official
---
# Seeed Studio XIAO ESP32S3 Sense｜板载器件和接线

原装相机用板对板接口，第一次测试只插 USB。要加 3.3 V I²C 模块，可用 D4 → SDA、D5 → SCL、3V3 和 GND。已经在 D8/D9/D10 接屏幕的项目，只在确认能让 SPI 设备共享并分别控制片选后保留。使用板上 SD 时，GPIO21 交给 SD 片选，另选引脚做状态灯。

[Seeed Sense 接口说明](https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/)
