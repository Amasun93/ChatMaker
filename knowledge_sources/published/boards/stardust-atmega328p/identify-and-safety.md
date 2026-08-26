---
schema_version: "1.0"
kind: knowledge-page
stable_id: stardust-atmega328p-identify-and-safety
board_id: stardust-atmega328p
section_id: identify-and-safety
source_refs: [source-stardust-atmega328p-observed]
---
# 识别与安全

当前实板由用户确认是自研“星尘板”。已观察到 CH340、ATmega328P 签名 `0x1E950F` 和 115200 引导程序；这些线索不能证明其他批次或版本相同。

接线时先断开 USB 和外部电源。不要依据通用 Nano 图片猜测星尘板未记录的针脚、板载器件或供电能力。
