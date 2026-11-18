---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-c3-devkitm-1-components-and-wiring
board_id: esp32-c3-devkitm-1
section_id: components-and-wiring
source_refs: [source-esp32-c3-devkitm-1-official]
---
# 板载器件和接线

先用板上的供电指示灯判断是否通电，再用可编程的 RGB 彩灯观察程序效果。彩灯自带控制器，需要通过程序发送颜色数据。

要加普通 LED，可先选一个已核对的空闲输出脚，把限流电阻和 `basic-led` 串联再接地。接传感器时逐一认出供电、地、信号，引出线颜色仅作辅助。一次只加一个元件，通电后先复查原有串口和彩灯是否还正常。

需要做壳子时，从官方尺寸图或手上的板实测外形，给 USB 插头、按键和天线留空间。紧配尺寸、插头能否到位及盖上壳后的无线效果都需要实物检查。

[乐鑫板卡原理图和尺寸资料](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32c3/esp32-c3-devkitm-1/user_guide.html#related-documents)
