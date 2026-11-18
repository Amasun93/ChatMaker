---
schema_version: "1.0"
kind: knowledge-page
stable_id: waveshare-esp32-s3-touch-lcd-2-8-toolchains-and-upload
board_id: waveshare-esp32-s3-touch-lcd-2-8
section_id: toolchains-and-upload
source_refs: [source-waveshare-esp32-s3-touch-lcd-2-8-official]
---
# 编译和写入

使用 ChatMaker 自带的 `chatmaker-hardware`，板卡 ID 是 `waveshare-esp32-s3-touch-lcd-2-8`。V2 参数为 `--revision v2`，会选择 CST3530。Windows x64 和受支持的 Mac 走托管 Arduino 路线。Arduino-ESP32 固定为 3.3.11，板卡和分区参数由适配器填写。Mind+ 不是此路线的依赖。

可以用 `--action prepare-environment --dry-run` 看还缺哪些工具。这一步只预览。首次确需编译时，ChatMaker 会准备编译器、ESP32-S3 板卡核心、烧录工具及正确版本的屏幕和触摸驱动。显示 `remaining_download_bytes: 0` 时，所需压缩包已有校验通过的缓存。第一次解包和准备驱动可能还要一点时间。

沿用同一个 `CHATMAKER_RUNTIME_ROOT` 可在后续项目复用已经校验的环境。工作区或工具目录换了、归档缺失或校验失败时，按当前工具报告处理。确认实物型号、版本和端口后，再执行上传。编译通过、成功写入和看到实物效果是三次检查。[微雪官方 V1/V2 资料](https://docs.waveshare.net/ESP32-S3-Touch-LCD-2.8/Resources-And-Documents/)
