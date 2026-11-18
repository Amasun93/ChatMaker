---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-c6-devkitc-1-components-and-wiring
board_id: esp32-c6-devkitc-1
section_id: components-and-wiring
source_refs: [source-esp32-c6-devkitc-1-official]
---
# 板载器件和接线

先用 USB 给板子供电。常亮的供电指示灯用于判断电源，板载可寻址 RGB 彩灯用程序发送颜色数据。用灯实验时观察彩灯是否按写好的顺序变色。

`J5` 是模组的电流测量接口，常规课堂连接保持出厂的短接状态。若插 USB 后有供电指示但模组没运行，再对照对应版本的官方图检查 J5 是否脱落。要加一个现成的传感器，先按模块实际丝印和本板排针表确认电源、地和信号，再逐一加线。

做外壳可查官方尺寸图。装壳之前接上两种 USB 用法所需的线，确认插头有空间，BOOT 和 RESET 可以按到。

[乐鑫电流测量说明](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32c6/esp32-c6-devkitc-1/user_guide.html#current-measurement) · [官方尺寸图入口](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32c6/esp32-c6-devkitc-1/user_guide.html#related-documents)
