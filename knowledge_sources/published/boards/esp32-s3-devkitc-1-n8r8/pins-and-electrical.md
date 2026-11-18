---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-s3-devkitc-1-n8r8-pins-and-electrical
board_id: esp32-s3-devkitc-1-n8r8
section_id: pins-and-electrical
source_refs: [source-esp32-s3-devkitc-1-n8r8-official]
---
# 引脚和电气规则

按对应版本的 J1、J3 表查排针丝印和 GPIO。外设接线需要共地。下面三类脚尤其容易选错。

- 原生 USB 的两根信号脚在板卡 `esp32-s3-devkitc-1-n8r8` 中已标为保留。要使用原生 USB 时，留给这项用途。走 USB 转串口时，也给板载 UART 的 `TX`、`RX` 留出空间。
- N8R8 的 `GPIO35`、`GPIO36`、`GPIO37` 用于板内的八线 PSRAM。排针上看得到编号，选外接引脚时仍要避开它们。
- BOOT 对应的脚与其他启动脚会在上电或复位时被读取，首次接开关和模块应避开。板载 RGB 的位置也随版本改变，详见「板载器件和接线」。

[乐鑫 v1.1 引脚表和存储占脚说明](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html) · [乐鑫 S3 启动脚说明](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/schematic-checklist.html)
