---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-c6-devkitc-1-libraries-and-examples
board_id: esp32-c6-devkitc-1
section_id: libraries-and-examples
source_refs: [source-esp32-c6-devkitc-1-official]
---
# 库和第一个示例

先做一个只用 Arduino 核心的草图，让它每秒打印 `C6_READY`。当前用转串口还是原生 USB 要在编译时选好，这样可以用正确的端口看结果。

下一步参考乐鑫 `BlinkRGB` 的 `rgbLedWrite`，按照板卡记录确认的 GPIO 发送颜色。通用示例里的 `RGB_BUILTIN` 要和实际载板核对。已从其他 ESP32 板拿来的课程草图，要重新核对供电、引脚和使用的库，再按 C6 构建。

仓库的 macOS 工作流用 `examples/chatduino/uno/blink` 做通用编译检查。当前作品的编译、写入、串口和彩灯观察各有自己的结果。

[乐鑫 Arduino BlinkRGB 示例](https://github.com/espressif/arduino-esp32/blob/3.3.12/libraries/ESP32/examples/GPIO/BlinkRGB/BlinkRGB.ino)
