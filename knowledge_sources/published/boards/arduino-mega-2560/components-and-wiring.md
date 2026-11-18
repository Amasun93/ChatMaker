---
schema_version: "1.0"
kind: knowledge-page
stable_id: arduino-mega-2560-components-and-wiring
board_id: arduino-mega-2560
section_id: components-and-wiring
source_refs: [source-arduino-mega-2560-official]
---
# 板载灯与接线

**先做只有一根线的作品。** 拔下扩展板和杜邦线，只接 USB 数据线。上电时 `ON` 灯亮，运行 Blink 后看标着 `L` 的灯按目标节奏亮灭。这个检查可先确认电脑到板子的基本流程。[Arduino 官方 Blink 例程](https://docs.arduino.cc/built-in-examples/basics/Blink)

- **外接 LED**。从已确认的数字输出串联适用的限流电阻接 LED，核对 LED 方向，连回 `GND`。先只点亮一颗，看到它按设定周期亮灭后再增加其他器件。
- **外接 I²C 屏**。先看屏幕控制器、引脚标签、供电和信号电平，把模块的 `SDA`、`SCL` 对到 Mega 同名接口，共地后先扫描地址，再用小例程显示一行文字。确认确实是对应的四针型号时，可参考 `ssd1306-i2c-128x64-module` 的模块识别资料，按 Mega 的板卡记录接线并重新验证这组搭配。[Arduino I²C 接线说明](https://docs.arduino.cc/learn/communication/wire)
- **外接舵机或电机**。按器件额定值选择电源和驱动，并依照接线图与 Mega 共地。先空载测试一次短动作，观察器件能否动作、板子是否保持运行。出现突然重启或线材发热时，断电后再检查接线与供电。
