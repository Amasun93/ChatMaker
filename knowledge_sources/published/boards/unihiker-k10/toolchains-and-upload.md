---
schema_version: '1.0'
kind: knowledge-page
stable_id: unihiker-k10-toolchains-and-upload
board_id: unihiker-k10
section_id: toolchains-and-upload
source_refs:
- source-unihiker-k10-official
---
# DFRobot UNIHIKER K10 行空板｜编译工具和上传

ChatMaker 准备 DFRobot 官方 K10 Arduino 核心 0.0.5 和它的下载工具。先在板型和端口确认后上传。进不了下载模式时，按住背面 BOOT，短按 RESET，再松开 BOOT，检查新端口。

[DFRobot Arduino 板卡包](https://www.unihiker.com.cn/wiki/k10/ArduinoIDE_prepare) · [DFRobot 下载模式](https://www.unihiker.com.cn/wiki/k10/firmware_upload)

在仓库目录里，第一条只查看还缺什么。需要时再执行去掉 `--dry-run` 的准备命令，第二条单独验证编译。

```powershell
chatmaker-hardware --board-id unihiker-k10 --action prepare-environment --dry-run
chatmaker-hardware --board-id unihiker-k10 --action compile --sketch examples/chatduino/unihiker-k10/board-rgb
```

让 ChatMaker 确认你的板型和端口后，把编译动作换成 `run`，由它带上 `--port` 和板型确认再下载。查看下载结果后，再确认板子实际出现了预期效果。
