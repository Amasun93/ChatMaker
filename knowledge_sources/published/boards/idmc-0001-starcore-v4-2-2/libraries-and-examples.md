---
schema_version: "1.0"
kind: knowledge-page
stable_id: idmc-0001-starcore-v4-2-2-libraries-and-examples
board_id: idmc-0001-starcore-v4-2-2
section_id: libraries-and-examples
source_refs:
  - source-idmc-0001-starcore-v4-2-2-owned-docs
---
# 扩展、库和示例模式

掌控板兼容目标先使用 `MPython.h`。它已经提供常用的 `display`、NeoPixel 类型和 Wire；OLED 或 WS2812 项目不要重复包含显示与灯带底层头文件，也不要默认换用 U8g2。DHT11、超声波、舵机和串口 MP3 分别需要对应 Mind+ 扩展提供的 `DFRobot_DHT.h`、`DFRobot_URM10.h`、`DFRobot_Servo.h`、`DFRobot_SerialMp3.h`。

可靠示例先做一个输入或一个输出：串口心跳、模拟原始值、按钮状态、OLED 英文、单色灯带。确认单模块结果后再组合。DHT11 每次读取间隔至少约 2.5 秒，并避免同一节拍连续调用两个 getter；超声波无效或超时返回值不能当作真实零距离；舵机和灯带使用外部电源并共地。

当前仓库已提供五个最小示例，并已使用当前 Mind+ 1.8 mPython 目标完成编译：

- OLED：只包含 `MPython.h`，使用内置 `display`，示例 `examples/chatduino/starcore/oled-i2c-hello/oled-i2c-hello.ino`
- LCD1602 I2C：`DFRobot_LiquidCrystal_I2C.h`，示例 `examples/chatduino/starcore/lcd1602-i2c-hello/lcd1602-i2c-hello.ino`
- WS2812：只包含 `MPython.h`，使用内置 `DFRobot_NeoPixel`，示例 `examples/chatduino/starcore/ws2812-strip/ws2812-strip.ino`
- SG90：`DFRobot_Servo.h`，示例 `examples/chatduino/starcore/servo-position/servo-position.ino`
- 超声波：`DFRobot_URM10.h`，示例 `examples/chatduino/starcore/ultrasonic-distance/ultrasonic-distance.ino`

代码能编译只代表语法、板型和库组合可用；由于目前没有实体板，烧录、串口结果和物理效果仍保持 `unverified`。
