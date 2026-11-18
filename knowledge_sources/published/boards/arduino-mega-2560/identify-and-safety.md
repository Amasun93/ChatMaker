---
schema_version: "1.0"
kind: knowledge-page
stable_id: arduino-mega-2560-identify-and-safety
board_id: arduino-mega-2560
section_id: identify-and-safety
source_refs: [source-arduino-mega-2560-official]
---
# 确认板型与用电安全

1. **看实物**。找到板上的 `MEGA 2560` 字样和主芯片上的 `ATMEGA2560` 标记，必要时用手机拍照放大。老款 Mega ATmega1280、Due 和 GIGA R1 WiFi 要按各自型号走流程。兼容板的 USB 芯片和接口可能不同，选板时先看主芯片。
2. **首次仅接数据线**。原版 Rev3 使用 USB-B，即板上近似方形的大接口。上电后找 `ON` 灯，然后在电脑上核对新出现的串口。若只有灯亮，换一根已知能传数据的线，直接接电脑再试。
3. **接模块前先断电**。把模块的供电范围和信号电平与 `arduino-mega-2560` 板卡记录核对。电平不同的信号按模块说明转换。连接独立供电的外设时按接线图处理共地，高电流负载由合适的驱动电路供电。

做外壳时对照官方机械资料留出 USB 插头、排针和复位按钮的空间，打印后用你手里的板确认装配。[Arduino 官方板卡、引脚和 CAD 资料](https://docs.arduino.cc/hardware/mega-2560/)
