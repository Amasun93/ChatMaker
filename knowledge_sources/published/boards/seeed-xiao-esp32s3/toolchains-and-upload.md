---
schema_version: '1.0'
kind: knowledge-page
stable_id: seeed-xiao-esp32s3-toolchains-and-upload
board_id: seeed-xiao-esp32s3
section_id: toolchains-and-upload
source_refs:
- source-seeed-xiao-esp32s3-official
---
# Seeed Studio XIAO ESP32S3｜编译工具和上传

两款 XIAO 共用正式的 `XIAO_ESP32S3` 编译定义。ChatMaker 从 ESP32-S3 已校验环境编译，启用 OPI PSRAM 和 USB 串口。USB 串口编号会随拔插或进入下载模式改变。

[Seeed 软件准备与 USB 下载](https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/)

在仓库目录里，第一条只查看还缺什么。需要时再执行去掉 `--dry-run` 的准备命令，第二条单独验证编译。

```powershell
chatmaker-hardware --board-id seeed-xiao-esp32s3 --action prepare-environment --dry-run
chatmaker-hardware --board-id seeed-xiao-esp32s3 --action compile --sketch examples/chatduino/xiao-esp32s3/usb-blink
```

让 ChatMaker 确认你的板型和端口后，把编译动作换成 `run`，由它带上 `--port` 和板型确认再下载。查看下载结果后，再确认板子实际出现了预期效果。
