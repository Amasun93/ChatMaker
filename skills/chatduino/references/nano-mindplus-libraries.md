# Mind+ Nano 库策略

## 无额外库优先

普通 LED、按钮、光敏模拟量、电位器、有源蜂鸣器、`tone()` 无源蜂鸣器和 HC-SR04 可用 Arduino 核心 API 完成，优先避免不必要的第三方库。

## 需要确认的库

| 模块 | Mind+ 常见头文件 | 规则 |
|---|---|---|
| DHT11 | `DFRobot_DHT.h` | 使用前先确认本机库存在并真实编译 |
| I²C SSD1306 | `DFRobot_SSD1306_I2C.h` | 只用于确认的 SSD1306 I²C 屏；地址先看资料或扫描 |
| 舵机 | `DFRobot_Servo.h` 或后端可用的 `Servo.h` | 不凭 Arduino IDE 经验猜 Mind+ 当前头文件 |
| WS2812 灯带 | Mind+ 对应 NeoPixel 库 | 先确认灯珠数、供电和 API；大电流外部供电 |

Mind+ 1.x 和 2.x 的库目录不完全相同。代码生成后必须交给实际选择的后端编译。出现 `No such file or directory` 时先补齐/确认库，而不是换一个陌生 API 让错误暂时消失。
