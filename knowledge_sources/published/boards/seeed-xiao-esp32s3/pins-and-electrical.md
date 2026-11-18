---
schema_version: '1.0'
kind: knowledge-page
stable_id: seeed-xiao-esp32s3-pins-and-electrical
board_id: seeed-xiao-esp32s3
section_id: pins-and-electrical
source_refs:
- source-seeed-xiao-esp32s3-official
---
# Seeed Studio XIAO ESP32S3｜引脚和电气规则

排针信号用 3.3 V。I²C 是 D4/SDA 对 GPIO5、D5/SCL 对 GPIO6。D2 对 GPIO3，启动时可能受外部电路影响。代码优先用 `D4` 这样的板卡符号；芯片编号 `4` 指 GPIO4。

[Seeed 引脚对照表](https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/)
