---
schema_version: '1.0'
kind: knowledge-page
stable_id: arduino-uno-r4-wifi-toolchains-and-upload
board_id: arduino-uno-r4-wifi
section_id: toolchains-and-upload
source_refs:
- source-arduino-uno-r4-wifi-official
---
# Arduino UNO R4 WiFi｜编译工具和上传

ChatMaker 准备 Arduino Renesas UNO 核心 1.6.0 和 Arduino CLI，并用官方板卡定义里的 BOSSA 写入主芯片。先关掉占用端口的串口窗口。保留板载无线模块的原有固件。

[Arduino 板卡资料](https://docs.arduino.cc/hardware/uno-r4-wifi/)

在仓库目录里，第一条只查看还缺什么。需要时再执行去掉 `--dry-run` 的准备命令，第二条单独验证编译。

```powershell
chatmaker-hardware --board-id arduino-uno-r4-wifi --action prepare-environment --dry-run
chatmaker-hardware --board-id arduino-uno-r4-wifi --action compile --sketch examples/chatduino/uno-r4-wifi/matrix-heart
```

让 ChatMaker 确认你的板型和端口后，把编译动作换成 `run`，由它带上 `--port` 和板型确认再下载。查看下载结果后，再确认板子实际出现了预期效果。
