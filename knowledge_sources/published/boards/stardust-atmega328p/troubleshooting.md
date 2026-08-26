---
schema_version: "1.0"
kind: knowledge-page
stable_id: stardust-atmega328p-troubleshooting
board_id: stardust-atmega328p
section_id: troubleshooting
source_refs: [source-stardust-atmega328p-observed]
---
# 按证据门排错

- 看不到端口：先检查 CH340 驱动和数据线。
- 57600 同步失败：当前已验证实板应改用 115200，不要连续盲试其他板型。
- 扫描不到 0x3C：断电检查 VCC、GND、A4/A5 和模块地址焊盘。
- 串口有 READY 但屏幕空白：继续检查地址、初始化、方向与供电；不能把串口成功写成屏幕成功。
- 断电重启：当前代表案例已由用户确认重新上电后恢复显示；其他程序或模块仍需单独验证，不能用上传后的自动复位代替。
