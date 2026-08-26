---
schema_version: "1.0"
kind: knowledge-page
stable_id: stardust-atmega328p-libraries-and-examples
board_id: stardust-atmega328p
section_id: libraries-and-examples
source_refs: [source-stardust-atmega328p-observed]
---
# 从代表案例开始

使用配方 `stardust-idmd-0021-oled-status` 和其登记的完整源码。案例只在启动时绘制一次，并在串口输出 `STARDUST_OLED_READY` 与持续心跳。

串口就绪标记可帮助定位程序运行状态，但仍需用户确认文字、方向、清晰度和闪烁情况。
