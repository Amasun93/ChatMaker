# AVR OLED 仪表盘编译记录

日期：2026-08-17

## Nano

- 源文件：`examples/chatduino/nano/oled-dashboard/oled-dashboard.ino`
- 后端：Mind+ 2.x Arduino CLI
- FQBN：`mindplus:avr:nano:cpu=atmega328`
- 结果：编译成功，返回码 0
- 程序空间：10360 / 30720 bytes
- 动态内存：585 / 2048 bytes

## Uno

- 源文件：`examples/chatduino/uno/oled-dashboard/oled-dashboard.ino`
- 后端：Mind+ 2.x Arduino CLI
- FQBN：`mindplus:avr:uno`
- 结果：编译成功，返回码 0
- 程序空间：10358 / 32256 bytes
- 动态内存：583 / 2048 bytes

两次编译均解析到 `DFRobot_Mindplus_SSD1306`、`Wire`、`DFRobot_Mindplus_ASCIIfont` 和 `DFRobot_Mindplus_CHfont`。当前没有检测到有线 Nano 或 Uno；烧录、串口、屏幕和按钮实物效果保持 `unverified`。
