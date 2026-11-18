---
schema_version: "1.0"
kind: knowledge-page
stable_id: arduino-mega-2560-pins-and-electrical
board_id: arduino-mega-2560
section_id: pins-and-electrical
source_refs: [source-arduino-mega-2560-official]
---
# Mega 引脚与电气规则

按 `arduino-mega-2560` 板卡记录确定已经登记的引脚。排针上数字很多，先找实物丝印，再用官方引脚图确定插孔位置和用途。[Arduino Mega 2560 官方引脚图](https://docs.arduino.cc/resources/pinouts/A000067-full-pinout.pdf)

- **板载灯**。程序用 `LED_BUILTIN` 控制 `L` 灯，插上 USB 就能测试。
- **I²C**。Mega 用板上标着 `SDA`、`SCL` 的一组信号。同名引出接的是同一条总线。从 Uno 或 Nano 搬程序时，把示例里的接线改为 Mega 的这组信号。
- **串口**。电脑 USB 调试与板上 `RX0`、`TX0` 共用主串口。外接串口模块优先用 `Serial1`，按图找 `RX1`、`TX1`。
- **模拟和 PWM**。读电位器等连续变化的信号时选 `ANALOG IN` 区的引脚。要调灯的亮度，先用引脚图找支持 PWM 的输出，并检查板上对应的 `~` 标记。
- **SPI**。从其他板搬 SPI 模块时，按 Mega 引脚图找 `MISO`、`MOSI`、`SCK`，确认模块的片选脚和程序设置。扩展板从 `ICSP` 取 SPI 时，核对插座位置和方向。

接线前核对模块供电、输入电平和地线。GPIO 用来传小电流信号，电机和舵机按模块资料选驱动与供电。[Arduino AVR 1.8.8 Mega 引脚定义](https://github.com/arduino/ArduinoCore-avr/blob/1.8.8/variants/mega/pins_arduino.h)
