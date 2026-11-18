---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-c6-devkitc-1-identify-and-safety
board_id: esp32-c6-devkitc-1
section_id: identify-and-safety
source_refs: [source-esp32-c6-devkitc-1-official]
---
# 识别板型和用电安全

载板型号看板上的字，存储规格看金属罩上的模组信息与包装或订购表。对照 v1.1 或 v1.2 手册认出两个 Type-C 口。一个经 USB 转串口芯片，另一个接 ESP32-C6 芯片本身。两个插口形状一样，选口时要看板上标识和示意图。

课堂先用一个 USB 口给板子供电。换线前拔掉 USB 和其他电源。板上的电源脚和信号脚各有用途，接 5 V 模块前先核对它输出的信号电平，再决定是否需要电平转换。电气要求见板卡 `esp32-c6-devkitc-1`。

[乐鑫 v1.2 板图和供电说明](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32c6/esp32-c6-devkitc-1/user_guide.html) · [乐鑫 v1.1 手册](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32c6/esp32-c6-devkitc-1/user_guide_v1.1.html)
