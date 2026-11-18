---
schema_version: "1.0"
kind: knowledge-page
stable_id: arduino-mega-2560-libraries-and-examples
board_id: arduino-mega-2560
section_id: libraries-and-examples
source_refs: [source-arduino-mega-2560-official]
---
# Arduino 库和起步示例

| 想验证的功能 | 从哪里开始 | 看到什么算成功 |
| --- | --- | --- |
| 板载灯 | 打开 Arduino IDE 的 `File → Examples → 01.Basics → Blink`，或让 ChatMaker 用 `LED_BUILTIN` 生成闪灯程序 | `L` 灯反复按设定间隔亮和灭 |
| 按钮输入 | 用内部上拉模式 `INPUT_PULLUP`，把确定的数字输入和 `GND` 通过按钮接通，先把状态打印到串口 | 松开读到 `HIGH`，按下读到 `LOW` |
| 电位器等模拟输入 | 按器件说明接到已核对的模拟输入，用 `analogRead()` 读取，再打印 | 转动或改变输入时，读数随之变化 |
| I²C 模块 | 用 Arduino 自带的 `Wire`，先查总线上实际出现的地址，再试一个对应控制器的例程 | 扫到接入的设备，随后实物显示或读数符合预期 |

ChatMaker 仓库的 `examples/chatduino/uno/blink/` 也用 `LED_BUILTIN`。仓库的 macOS 编译任务把它交给 Mega 编译目标，可用这个目录做一次独立的编译检查。[ChatMaker 的 macOS 编译流程](https://github.com/Amasun93/ChatMaker/blob/main/.github/workflows/macos-hardware.yml)

先编译最小程序，再一次加一个功能。第三方库先确认库名、版本和是否支持 Arduino AVR。ChatMaker 如需安装锁定清单里的库，可用 `--library` 指定已支持的库项并预览准备步骤。旧项目用了 Mind+ 的 `DFRobot_*` 头文件时，按原项目补齐对应库，或换成明确支持 Mega 的 Arduino 库后重新编译。沿用别的板的现成例程时，先按 Mega 板卡记录检查接线，再确认编译目标。

[Arduino 官方 Blink](https://docs.arduino.cc/built-in-examples/basics/Blink) · [Arduino 内部上拉示例](https://docs.arduino.cc/built-in-examples/digital/InputPullupSerial) · [Arduino Wire 说明](https://docs.arduino.cc/learn/communication/wire)
