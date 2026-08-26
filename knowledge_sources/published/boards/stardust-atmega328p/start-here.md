---
schema_version: "1.0"
kind: knowledge-page
stable_id: stardust-atmega328p-start-here
board_id: stardust-atmega328p
section_id: start-here
source_refs: [source-stardust-atmega328p-observed]
---
# 从精确的星尘板身份开始

先读取板卡记录 `stardust-atmega328p`。当前产品名来自用户确认，ATmega328P、CH340 和 Nano 兼容目标只是电子与工具链证据，不能把产品改称 Arduino Nano。机械尺寸、完整针脚和具体硬件版本仍待自研资料或实测。

当前最小闭环是 IDMD-0021 OLED 状态页。编译、上传、串口、断电重启和肉眼显示必须分别报告。
