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

串口就绪标记可帮助定位程序运行状态，但不能代替肉眼检查。本次连接的 IDMD-0021 OLED 已由用户确认显示内容正常；其他模块或硬件批次仍需单独验证。
