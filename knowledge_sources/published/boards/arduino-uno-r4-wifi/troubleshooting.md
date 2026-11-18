---
schema_version: '1.0'
kind: knowledge-page
stable_id: arduino-uno-r4-wifi-troubleshooting
board_id: arduino-uno-r4-wifi
section_id: troubleshooting
source_refs:
- source-arduino-uno-r4-wifi-official
---
# Arduino UNO R4 WiFi｜课堂常见问题和排错

- 没有端口 → 换一根可传数据的 USB-C 线，拔插观察哪个端口改变。
- 选板后提示找不到工具 → 先看准备预览，再准备 Renesas 环境。
- 点阵空白 → 检查是否用了 R4 WiFi 的示例，查看串口输出与实际写入状态。
- Qwiic 读不到模块 → 核实模块支持 3.3 V，并把示例初始化改为 `Wire1`。

[ChatMaker 本轮验证与复测](https://github.com/Amasun93/ChatMaker/blob/main/docs/verification/2026-11-18-classroom-boards.md)
