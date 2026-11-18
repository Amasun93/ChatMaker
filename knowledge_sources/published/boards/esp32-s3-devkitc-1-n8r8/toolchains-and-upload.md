---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-s3-devkitc-1-n8r8-toolchains-and-upload
board_id: esp32-s3-devkitc-1-n8r8
section_id: toolchains-and-upload
source_refs: [source-esp32-s3-devkitc-1-n8r8-official]
---
# 编译工具和上传

用 `chatmaker-hardware --board-id esp32-s3-devkitc-1-n8r8`，按板卡记录使用适合 N8R8 的 Flash、分区和八线 PSRAM 配置。首次用 `prepare-environment --dry-run` 看准备计划，再实际准备。之后可用 `doctor` 查看是否已经就绪。

- 板上 USB-to-UART 对应 `--usb-mode uart`。板图标出的 ESP32-S3 USB 口对应 `--usb-mode native`，此路线让 Arduino 的 `Serial` 通过芯片的 USB 串口输出。两个插口形状相同，先认板图，再编译。
- 用 `compile` 时只生成构建结果。写入前，通过 `ports` 确认插拔时新增的端口，核对实物、草图和目标后，用 `run` 设置 `--board-confirmed` 与实际端口。
- 烧录后原生 USB 端口可能重新出现。打开当前程序的端口，读串口，再观察外设和断电重启。

[乐鑫 S3 开发板 USB 接口](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.0.html#description-of-components) · [Arduino USB CDC 说明](https://docs.espressif.com/projects/arduino-esp32/en/latest/tutorials/cdc_dfu_flash.html)
