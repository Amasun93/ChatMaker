---
schema_version: "1.0"
kind: knowledge-page
stable_id: microbit-v2-troubleshooting
board_id: microbit-v2
section_id: troubleshooting
source_refs: [source-microbit-v2-official]
---
# 按证据门逐步排错

- 找不到目标盘：确认卷标为 `MICROBIT`，并检查 `DETAILS.TXT`；不要选择普通 U 盘或 `MAINTENANCE`。
- 有多个目标：明确选择当前板卡，禁止猜测写入。
- 写入后出现 `FAIL.TXT`：读取其中的 DAPLink 错误，程序不能记为上传成功。
- 文件已复制但没有效果：继续检查设备是否重新连接、串口是否出现、程序是否启动；复制动作本身不能证明实体效果。
- LED 或按键异常：先用最小代表案例排除程序和下载问题，再检查 V2 专属 API 与资源占用。
- 断电结果未知：真实拔电再上电，单独记录程序是否恢复；不要用上传后的自动复位代替。
