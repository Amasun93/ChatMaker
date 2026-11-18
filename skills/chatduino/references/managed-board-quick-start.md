# 板卡速查｜教室里先做哪一步

先看板子写着什么型号，再按这一行选择入口。用户只想选板、了解功能或检查接线时，可以先用板卡记录和这里的资料。需要编译或写入时，再检查该板的工具是否已准备好。完整源码中，每块板的 Wiki 都用表中的板卡 ID 找到。

| 板卡 | 板卡 ID 与开始方式 |
| --- | --- |
| Arduino Uno R3 | `arduino-uno-r3`。使用 `chatmaker-hardware` 的 Uno R3 目标，可先观察板载灯闪烁。接线使用 Uno R3 的引脚图。 |
| 经典 Arduino Nano | `arduino-nano-classic`。确认板上是 ATmega328P，再用 Nano 工具路线。已有引导程序信息时按实际版本选。[Nano 入门](nano-beginner-guidance.md) |
| Arduino Mega 2560 Rev3 | `arduino-mega-2560`。通过 `chatmaker-hardware` 走 Mega 的 AVR 目标。可先试板载灯。用外接模块时，先核对电压和 Mega 自己的引脚图。 |
| DOIT ESP32 DevKit V1 | `esp32-devkit-v1`。确认载板和 ESP-WROOM-32，再按 [经典 ESP32 说明](esp32-doit-devkit-v1.md)选择例程。 |
| ESP32-C3-DevKitM-1 | `esp32-c3-devkitm-1`。确认 DevKitM-1 和适配的 4 MB 模组，从板上 USB 转串口入口开始。板载 RGB 需要对应的可寻址灯示例。 |
| ESP32-C6-DevKitC-1 | `esp32-c6-devkitc-1`。按 8 MB 的板型准备。看 USB 插在哪一端，转串口选 `uart`，芯片直连口选 `native`。 |
| ESP32-S3-DevKitC-1 N8R8 | `esp32-s3-devkitc-1-n8r8`。核对模组上的 N8R8。USB 方式按实际插口选。使用板载 RGB 前先确认载板修订。 |
| 微雪 ESP32-S3-Touch-LCD-2.8 | `waveshare-esp32-s3-touch-lcd-2-8`。先看背面 V1 或 V2，再走[屏幕和触摸板说明](waveshare-s3-touch-lcd-2-8.md)。 |
| 星核板 v4.2.2 | `idmc-0001-starcore-v4-2-2`。确认主控版本。Windows x64 可走托管编译，模块和接线按[星核课堂模块说明](starcore-classroom-modules.md)核对。 |
| 经典掌控板 V2.x | `mpython-classic-v2x`。确认经典型号，再走对应编译路线。实物修订可能影响板载器件，先核对要用的功能。 |
| 掌控板 3.0 | `mpython-v3`。确认是 3.0 彩屏板，再按 3.0 的独立工具路线和屏幕例程开始。 |
| micro:bit V2 | `microbit-v2`。先确认版本，用 `chatmaker-microbit` 准备 MicroPython 项目并生成 HEX，写入目标由对应开发板和盘符决定。 |
| 星辰板 | `stardust-atmega328p`。用 `chatmaker-stardust` 和已核对的兼容编译配置。额外引脚以实物和完整引脚资料为准。 |
| 行空板 M10 | `unihiker-m10`。用 `chatmaker-unihiker` 检查完整 Python 项目，再按 [M10 说明](unihiker-m10.md) 选择同步和运行方式。 |

Nova 的 `nova-esp32` 是已确认经典 ESP32-D0WD-V3、4 MB Flash 后可选的编译配置。USB 转串口芯片的名字不足以确认板型。OLED 示例对应 SSD1306 和已核对的接线。准备采用例子前，先核对学生手上那块板的丝印、Flash 和模块。

## 常见的三个卡点

- **一上来要下载工具。** 先用具体板型的准备预览查看缺什么。待下载量为 0 时，可以复用已校验的文件。第一次解包和编译仍会花时间。后续项目尽量沿用同一个 ChatMaker 工具目录。
- **电脑看不到板子。** 先换一根确认能传数据的 USB 线，再看电脑是否出现端口、盘符或 M10 的 USB 网络入口。出现多块板时，核对实际要操作的那一块。
- **程序写了，预期效果没出来。** 先确认是否已经写入和重新启动，再看板上的灯、屏幕或串口。编译、写入和看到效果分别记录。
