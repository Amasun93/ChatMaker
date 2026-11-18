---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-s3-devkitc-1-n8r8-libraries-and-examples
board_id: esp32-s3-devkitc-1-n8r8
section_id: libraries-and-examples
source_refs: [source-esp32-s3-devkitc-1-n8r8-official]
---
# 库和第一个示例

- 先做只用 Arduino 核心的串口程序，每秒打印 `S3_READY`。能用正确的端口看到这行字，就有了程序运行的证据。
- 彩灯参考乐鑫 `BlinkRGB` 的 `rgbLedWrite`。通用设备定义里的 `RGB_BUILTIN` 要和实际载板版本核对。程序从低亮度开始，观察亮、灭、换色。
- 项目需要较大内存时，再给草图加入 PSRAM 初始化或查询结果的输出，确认内存可用后再增加摄像头或图像缓冲。

仓库的 macOS 工作流把 `examples/chatduino/uno/blink` 用作通用编译检查。板载彩灯和 PSRAM 的运行表现需在这块实物上单独观察。

[乐鑫 BlinkRGB 示例](https://github.com/espressif/arduino-esp32/blob/3.3.12/libraries/ESP32/examples/GPIO/BlinkRGB/BlinkRGB.ino) · [乐鑫 Arduino-ESP32 Flash/PSRAM 配置排错](https://docs.espressif.com/projects/arduino-esp32/en/latest/troubleshooting.html#how-to-determine-the-module-version)
