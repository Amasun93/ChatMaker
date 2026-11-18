---
schema_version: '1.0'
kind: knowledge-page
stable_id: seeed-xiao-esp32s3-sense-toolchains-and-upload
board_id: seeed-xiao-esp32s3-sense
section_id: toolchains-and-upload
source_refs:
- source-seeed-xiao-esp32s3-sense-official
---
# Seeed Studio XIAO ESP32S3 Sense｜编译工具和上传

ChatMaker 选 Sense 条目，底层沿用同一 `XIAO_ESP32S3` 目标，已设 OPI PSRAM。摄像头初始化用原装排线的引脚映射。先关掉串口监视器再下载。

[Seeed 相机工具准备](https://wiki.seeedstudio.com/xiao_esp32s3_camera_usage/)

在仓库目录里，第一条只查看还缺什么。需要时再执行去掉 `--dry-run` 的准备命令，第二条单独验证编译。

```powershell
chatmaker-hardware --board-id seeed-xiao-esp32s3-sense --action prepare-environment --dry-run
chatmaker-hardware --board-id seeed-xiao-esp32s3-sense --action compile --sketch examples/chatduino/xiao-esp32s3-sense/camera-check
```

让 ChatMaker 确认你的板型和端口后，把编译动作换成 `run`，由它带上 `--port` 和板型确认再下载。查看下载结果后，再确认板子实际出现了预期效果。
