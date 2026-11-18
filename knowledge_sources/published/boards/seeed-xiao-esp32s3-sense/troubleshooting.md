---
schema_version: '1.0'
kind: knowledge-page
stable_id: seeed-xiao-esp32s3-sense-troubleshooting
board_id: seeed-xiao-esp32s3-sense
section_id: troubleshooting
source_refs:
- source-seeed-xiao-esp32s3-sense-official
---
# Seeed Studio XIAO ESP32S3 Sense｜课堂常见问题和排错

- 串口里提示相机初始化失败 → 先断电，再检查 Sense 扩展板和排线就位。
- 在拍照示例看到缺少 PSRAM → 查看选的板型和 OPI PSRAM 设置。
- 写入后端口消失 → 换数据线，必要时按住 BOOT 插 USB，再选新端口。
- SD 和灯不能同时按预期工作 → 查 GPIO21 共用情况，把状态灯移到独立引脚。

[ChatMaker 本轮验证与复测](https://github.com/Amasun93/ChatMaker/blob/main/docs/verification/2026-11-18-classroom-boards.md)
