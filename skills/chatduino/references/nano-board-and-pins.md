# Arduino Nano ATmega328P 引脚规则

## 默认板型

本 Skill 的“Nano”指经典 Arduino Nano：ATmega328P、5 V、16 MHz。Nano Every、Nano ESP32、Nano 33 系列和 ATmega168 不共用本规则。

| 功能 | 可用引脚 | 课堂规则 |
|---|---|---|
| 数字输入/输出 | D2-D13、A0-A5 | D0/D1 默认保留给 USB 串口 |
| 模拟输入 | A0-A7 | 10 位 ADC，通常返回 0-1023 |
| 仅模拟输入 | A6、A7 | 禁止 `pinMode`、`digitalRead/Write` 和 PWM |
| PWM | D3、D5、D6、D9、D10、D11 | `analogWrite` 范围 0-255 |
| 外部中断 | D2、D3 | 需要快速事件时优先 |
| I²C | A4/SDA、A5/SCL | OLED 等 I²C 模块固定占用 |
| SPI | D10/SS、D11/MOSI、D12/MISO、D13/SCK | 使用 SPI 模块时整组保留 |
| UART | D0/RX、D1/TX | 与 USB 上传/串口监视器共用 |

## 默认分配

- 普通 LED：D6（需要调光时可 PWM）。
- 按钮或数字传感器：D2、D4、D7、D8。
- 光敏/电位器等模拟量：A0、A1；输入较多时再用 A6/A7。
- 舵机控制：D9；舵机电源通常用独立 5 V，并与 Nano 共地。
- HC-SR04：TRIG=D7，ECHO=D8。
- DHT11：DATA=D4。
- I²C OLED：SDA=A4，SCL=A5。
- SPI 模块占用 D10-D13 后，不再把这些引脚分给其他模块。

## 串口与烧录

烧录和串口监视器会使用 USB 串口。外接串口模块优先使用 `SoftwareSerial`；接收优先选择 D2/D3，发送可选其他空闲数字引脚。烧录前若外设占用 D0/D1，先断开其 TX/RX，避免上传失败。
