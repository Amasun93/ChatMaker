---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-s3-devkitc-1-n8r8-identify-and-safety
board_id: esp32-s3-devkitc-1-n8r8
section_id: identify-and-safety
source_refs: [source-esp32-s3-devkitc-1-n8r8-official]
---
# 识别板型和用电安全

核对金属罩上的 `ESP32-S3-WROOM-1` 和 `N8R8`。Flash 有 8 MB，用于保存程序和设置；另有 8 MB 八线（Octal SPI）PSRAM，给程序运行时放临时数据。`N8`、`N8R2`、`N16R8` 的存储配置各自不同。标着 `WROOM-1U` 的版本还要对照对应的外接天线配置。

把 v1.0 或 v1.1 和 N8R8 分开记录。载板版本不清楚时，先执行串口步骤，彩灯接法等认清对应的板图后再用。先用单根 USB 数据线供电。改线前断开电源，接 5 V 外设前核对信号电平。硬件和电气要求见板卡记录 `esp32-s3-devkitc-1-n8r8`。

[乐鑫 v1.0 订购资料](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.0.html#ordering-information) · [乐鑫 v1.1 硬件版本说明](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html#hardware-revision-details)
