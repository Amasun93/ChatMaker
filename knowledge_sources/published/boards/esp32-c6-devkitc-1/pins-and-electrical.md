---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-c6-devkitc-1-pins-and-electrical
board_id: esp32-c6-devkitc-1
section_id: pins-and-electrical
source_refs: [source-esp32-c6-devkitc-1-official]
---
# 引脚和电气规则

先读板子丝印，再按乐鑫 J1、J3 表查脚的用途。输出脚连外设信号，两个设备连接时也要共地。

- 原生 USB 使用 `GPIO12` 和 `GPIO13`。用这条 USB 路线时，给它们留出空间。USB 转串口则使用官方排针表里的 `TX`、`RX`。
- 启动脚在上电或重启时会被芯片读取。板载 RGB 数据脚、BOOT 键对应脚，以及排针表标出的其他启动脚都要先避开，免得外部电路让板子启动方式改变。
- `NC` 表示未连接，接外设前先在板图上找到实际可用的脚。用模拟传感器时再核对 ADC 脚和量程，实验数据还可能受板子批次的 ADC 校准影响。

[乐鑫 v1.2 排针表和启动脚注释](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32c6/esp32-c6-devkitc-1/user_guide.html#header-block) · [硬件版本和 ADC 批次说明](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32c6/esp32-c6-devkitc-1/user_guide.html#hardware-revision-details)
