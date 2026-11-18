---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-c3-devkitm-1-identify-and-safety
board_id: esp32-c3-devkitm-1
section_id: identify-and-safety
source_refs: [source-esp32-c3-devkitm-1-official]
---
# 识别板型和用电安全

板子中间有金属罩，罩上的字是模组名，载板本身还要核对 `DevKitM-1`。官方资料覆盖 `ESP32-C3-MINI-1` 和带外接天线座的 `ESP32-C3-MINI-1U`，常见订购项为带板载天线的 MINI-1。仅有“C3”字样时，继续核对载板和插口。电脑显示的串口名称只用于找到连接目标。

先用一根 USB 数据线供电，拔掉 USB 和独立电源后再改线。信号电平和供电方式按板卡 `esp32-c3-devkitm-1` 核对。板上的 `5V` 是电源脚。外设若用 5 V，先检查它的信号能否直接接入，必要时加电平转换。

[乐鑫外观、供电与排针说明](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32c3/esp32-c3-devkitm-1/user_guide.html)
