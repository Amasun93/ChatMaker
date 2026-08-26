---
schema_version: "1.0"
kind: knowledge-page
stable_id: stardust-atmega328p-components-and-wiring
board_id: stardust-atmega328p
section_id: components-and-wiring
source_refs: [source-stardust-atmega328p-observed]
---
# 当前验证组合

IDMD-0021 OLED 使用 VCC→5V、GND→GND、SDA→A4、SCL→A5。自研原理图确认 SSD1306、128×64、3.3V/5V 和 0x3C/0x3D 地址选择；当前连接单元在 0x3C 应答。

断电接线，上电后先扫描地址，再运行静态显示案例。不要循环清屏，以免明显闪烁。
