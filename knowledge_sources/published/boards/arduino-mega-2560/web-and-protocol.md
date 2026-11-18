---
schema_version: "1.0"
kind: knowledge-page
stable_id: arduino-mega-2560-web-and-protocol
board_id: arduino-mega-2560
section_id: web-and-protocol
source_refs: [source-arduino-mega-2560-official]
---
# USB 串口、网页与外接串口

1. **先让电脑收到一行**。让程序经 `Serial` 定时发出一行可辨认的文字，例如 `READY`。电脑端选与刚连接的 Mega 对应的端口，波特率和程序中的 `Serial.begin(...)` 保持一致。反复看到完整文字，说明这一段串口链路已通。打开串口监视器时板子可能复位，给程序一点启动时间。
2. **外接模块优先走 `Serial1`**。按官方图找到 `TX1`、`RX1`，模块的 TX 接板的 RX，模块的 RX 接板的 TX。接之前先核对电平和共地。把模块的回应经 `Serial` 打印回电脑，先测试一条请求和回应。[Arduino 官方引脚图](https://docs.arduino.cc/resources/pinouts/A000067-full-pinout.pdf) · [Arduino MultiSerialMega](https://docs.arduino.cc/built-in-examples/communication/MultiSerialMega)
3. **网页先定一条消息格式**。例如每条读数占一行，网页先显示收到的原始文字，再解析数值。用 Web Serial 时，通过支持它的浏览器对当前页面授权实际端口。同一时刻只留一个串口连接。[Chrome Web Serial 文档](https://developer.chrome.com/docs/capabilities/serial)Mega 2560 Rev3 若要通过网络和网页通信，需要另接合适的联网模块或由电脑做桥接。
4. **保留实际观察**。ChatMaker 的 `run` 可接收 `expected_serial_marker` 和 `serial_baudrate` 作为请求字段。只有收到约定文本才记录串口运行证据。用眼睛确认灯、屏幕和其他输出达到目标后，再记录实物验收结果。

[Arduino Mega 2560 官方资料](https://docs.arduino.cc/hardware/mega-2560/) · [Arduino CLI 串口复位机制](https://docs.arduino.cc/arduino-cli/platform-specification)
