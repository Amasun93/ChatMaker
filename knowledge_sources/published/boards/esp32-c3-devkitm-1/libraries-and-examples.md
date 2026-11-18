---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-c3-devkitm-1-libraries-and-examples
board_id: esp32-c3-devkitm-1
section_id: libraries-and-examples
source_refs: [source-esp32-c3-devkitm-1-official]
---
# 库和第一个示例

- 第一个草图只让 `Serial` 每秒发送一行，例如 `C3_READY`。它只需 Arduino 核心，便于先确认编译、写入、启动和串口。
- 做板载彩灯时，查看乐鑫 `BlinkRGB` 的 `rgbLedWrite` 用法，依据本板官方图核对数据脚。若程序依赖的通用 `RGB_BUILTIN` 缺失或不符，可把板卡记录确认的真实 GPIO 明确传给函数。
- 增加显示屏时才引入显示库。拿到含 `DFRobot_*` 头文件的旧程序，先找出原库和实际硬件，再决定能否使用兼容库或重新写驱动。

仓库的 macOS 工作流用 `examples/chatduino/uno/blink` 做通用编译检查。板载彩灯按上面的 RGB 做法另行编写，编译、写入和灯光效果在当前项目上分别记录。

[乐鑫 Arduino BlinkRGB 示例](https://github.com/espressif/arduino-esp32/blob/3.3.12/libraries/ESP32/examples/GPIO/BlinkRGB/BlinkRGB.ino)
