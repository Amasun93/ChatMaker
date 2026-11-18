---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-c6-devkitc-1-toolchains-and-upload
board_id: esp32-c6-devkitc-1
section_id: toolchains-and-upload
source_refs: [source-esp32-c6-devkitc-1-official]
---
# 编译工具和上传

ChatMaker 用精确板卡 `--board-id esp32-c6-devkitc-1` 选择独立 Arduino 工具和当前板卡存储配置。首次可用 `prepare-environment --dry-run` 看准备计划，再实际准备。如 `doctor` 显示已就绪，可直接使用现有工具。

1. 把数据线插到 USB 转串口时填 `--usb-mode uart`，插到 ESP32-C6 自带的 USB 时填 `--usb-mode native`。用哪个插口，在编译时就选好。
2. 用 `compile` 只构建程序。准备写入时用 `ports` 对比插拔前后的列表，确认本板、草图和端口，才用 `run` 加 `--board-confirmed` 和实际端口。
3. 原生 USB 模式下，程序的 `Serial` 走芯片的 USB 串口。烧录后如果连接重新出现，按当前程序的端口打开监视器。保留编译、上传、串口和实物效果各自的结果。

[乐鑫 v1.2 的两个 USB 口](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32c6/esp32-c6-devkitc-1/user_guide.html#description-of-components) · [乐鑫 C6 USB Serial/JTAG 指南](https://docs.espressif.com/projects/esp-idf/en/v5.5.6/esp32c6/api-guides/usb-serial-jtag-console.html)
