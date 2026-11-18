---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-s3-devkitc-1-n8r8-components-and-wiring
board_id: esp32-s3-devkitc-1-n8r8
section_id: components-and-wiring
source_refs: [source-esp32-s3-devkitc-1-n8r8-official]
---
# 板载器件和接线

板载可寻址彩灯只需 USB 供电和程序就能做入门实验。乐鑫手册标明初版 v1.0 的彩灯数据脚为 `GPIO48`，v1.1 改为 `GPIO38`。先确认载板硬件版本，再让程序向这个引脚发送颜色。色彩变化由彩灯显示，板上的电源灯亮表示有供电。

加外部 `basic-led` 时，另选已经核对的空闲脚，把限流电阻与 LED 串联再接地。下一次只加一个传感器，避免同时改变供电和几根信号线。做外壳时，对照相应版本尺寸图，并检查插头和按键的实际避让。

[乐鑫彩灯版本差异](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html#hardware-revision-details) · [乐鑫 v1.0 尺寸图入口](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.0.html#related-documents)
