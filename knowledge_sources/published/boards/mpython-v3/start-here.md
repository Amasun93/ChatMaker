---
schema_version: "1.0"
kind: knowledge-page
stable_id: mpython-v3-start-here
board_id: mpython-v3
section_id: start-here
source_refs: [source-mpython-v3-official]
---
# 先确认彩屏的掌控板 3.0

掌控板 3.0 使用 ESP32-S3 和 320×172 彩色屏，不是 128×64 单色 OLED 的经典掌控板。接板后先自动识别芯片和已有固件；仍不确定时查看“掌控板 3.0”丝印，或拍正反面照片让 AI 识别。

确认后只加载 `mpython-v3` 的引脚、显示和工具链资料。经典版代码中的 `oled`、经典 GPIO 映射和 mPython ESP32 编译目标不能直接复用。

