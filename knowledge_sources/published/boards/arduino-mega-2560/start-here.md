---
schema_version: "1.0"
kind: knowledge-page
stable_id: arduino-mega-2560-start-here
board_id: arduino-mega-2560
section_id: start-here
source_refs: [source-arduino-mega-2560-official]
---
# Arduino Mega 2560 入门

这页对应 Arduino Mega 2560 Rev3，ChatMaker 板卡 ID 为 `arduino-mega-2560`。先看板子上写的型号，确认主芯片是 ATmega2560。编译前无需插板，首次写入时用能传数据的 USB 线连接实物。[Arduino Mega 2560 Rev3 官方资料](https://docs.arduino.cc/hardware/mega-2560/)

1. **工具已经就绪**。把想看到的效果告诉 ChatMaker，例如“让 Mega 2560 的板载灯亮一秒、灭一秒，循环执行”。保存程序并编译，选定刚插入的端口后写入。入门作品可以只接 USB，观察板上的 `L` 灯。
2. **第一次需要准备工具**。ChatMaker 会先检查本机。工具缺失时可以预览还要下载的内容。请让准备步骤完成，再用同一份程序编译。以后使用同一个工具目录可复用环境。
3. **只是问怎么接线**。直接按这份 Wiki 和板卡记录查，等到要编译时再检查工具。

[识别与安全](identify-and-safety.md) · [引脚与电气](pins-and-electrical.md) · [编译与写入](toolchains-and-upload.md) · [器件和接线](components-and-wiring.md) · [库与示例](libraries-and-examples.md) · [通信](web-and-protocol.md) · [课堂排错](troubleshooting.md)
