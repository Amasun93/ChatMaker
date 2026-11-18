---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-c3-devkitm-1-pins-and-electrical
board_id: esp32-c3-devkitm-1
section_id: pins-and-electrical
source_refs: [source-esp32-c3-devkitm-1-official]
---
# 引脚和电气规则

板上印的 `IO3` 对应程序里的 `GPIO3`。按官方 J1、J3 排针表核对方向，避免把表里的排针顺序号当成 GPIO 编号。连接外设要把双方的地连起来。

- 上电或重启时，芯片用几根引脚上的电平决定启动方式。先避开官方排针表标注的启动脚，包括与板载彩灯及 BOOT 键有关的引脚。
- `TX`、`RX` 与板载 USB 转串口相连。课堂上要继续看串口日志时，先留给原用途。
- `IO18`、`IO19` 有芯片原生 USB 功能。电脑插到本板的 Micro-USB 时走的是另一条 USB 转串口线路，照搬带原生 USB 插口的 C3 板接法会选错通信路线。

[乐鑫排针表和启动脚注释](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32c3/esp32-c3-devkitm-1/user_guide.html#header-block)
