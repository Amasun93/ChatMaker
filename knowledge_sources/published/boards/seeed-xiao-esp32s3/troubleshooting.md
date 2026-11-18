---
schema_version: '1.0'
kind: knowledge-page
stable_id: seeed-xiao-esp32s3-troubleshooting
board_id: seeed-xiao-esp32s3
section_id: troubleshooting
source_refs:
- source-seeed-xiao-esp32s3-official
---
# Seeed Studio XIAO ESP32S3｜课堂常见问题和排错

- 没看到端口 → 换数据线。必要时按住 BOOT 插上 USB，再松开，选新出现的端口。
- 写入后串口不显示 → 重新查当前端口并打开 115200，短按 RESET 后看周期输出。
- I²C 扫不到 → 先核对 SDA 接 D4、SCL 接 D5，再检查共地和供电。
- 项目需要摄像头 → 核对是否有 Sense 相机扩展板，再走对应条目。

[ChatMaker 本轮验证与复测](https://github.com/Amasun93/ChatMaker/blob/main/docs/verification/2026-11-18-classroom-boards.md)
