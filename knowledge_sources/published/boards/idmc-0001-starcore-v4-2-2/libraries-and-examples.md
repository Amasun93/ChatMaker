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

源资料含有已编译和部分实物反馈，但 ChatMaker 当前仓库尚未把星核板示例复制并重新编译。因此本页提供的是清洗后的选择规则，不把历史证据提升为当前项目的编译或实物通过状态。
