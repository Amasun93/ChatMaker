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

## 板载 QMI8658 加速度与手势

星核板 v4.2.2 的加速度传感器已经焊在板上。在 Mind+ 上传模式选择“掌控板”后，可直接使用控制器分类中的三轴加速度、合加速度、校准和倾斜/摇晃手势积木；底层积木标识包括 `esp32.esp32_acceleration`、`esp32.esp32_accelerationCalibration`、`esp32.isGesture` 和 `esp32.onGesture`。这不是外接 LIS2DH12，不需要添加 `sen0224` 扩展。

Arduino/C++ 只需要 `MPython.h`。`mPython.begin()` 会初始化板载对象并自动探测 QMI8658（I2C `0x6B`）；之后使用全局对象 `accelerometer`：

```cpp
#include <MPython.h>

void setup() {
  Serial.begin(115200);
  mPython.begin();
}

void loop() {
  Serial.printf("x=%.0f y=%.0f z=%.0f strength=%.0f mg\n",
                accelerometer.getX(), accelerometer.getY(),
                accelerometer.getZ(), accelerometer.getStrength());
  delay(100);
}
```

`getX()`、`getY()`、`getZ()` 和 `getStrength()` 的单位是 mg（约 1000 mg 等于 1 g）。手势接口为 `isGesture()` / `onGesture()`，可使用 `MSA300::Shake`、`MSA300::TiltLeft`、`MSA300::TiltRight`、`MSA300::TiltForward` 和 `MSA300::TiltBack`。`MSA300` 是库为了兼容旧硬件保留的类名；v4.2.2 的实物仍是 QMI8658。安装方向会改变 X/Y 轴和“前后左右”的含义，体感游戏应先显示原始值，再让用户按实际握持方向校准阈值。

上面的最小程序已使用当前 Mind+ 1.8 星核板目标真实编译通过。它尚未证明当前板卡上传、串口数值、安装方向或体感效果，连接实物后仍要分别验证。

QMI8658 是六轴芯片，硬件同时含三轴陀螺仪；但当前已审查的 `MPython.h` 全局对象只公开加速度和手势方法，没有公开陀螺仪读数。需要角速度时，应另建“驱动验证”任务，先核对寄存器配置、量程、单位、轴向和与现有初始化的冲突，不能把 `getX/Y/Z()` 误称为陀螺仪。

## 板载 A/B 按键与无源蜂鸣器

A 键为 P5/GPIO0，B 键为 P11/GPIO2，按下为低电平。使用 `MPython.h` 的全局 `buttonA`、`buttonB` 或组合对象 `buttonAB`；常用方法是 `isPressed()`、`setPressedCallback()` 和 `setUnPressedCallback()`。库内部已做约 50 ms 的按下确认，但项目仍应以状态变化触发动作，避免按住时在 `loop()` 中反复执行。

板载无源蜂鸣器在 P6/GPIO16，使用全局 `buzz`。持续音可用 `buzz.freq(频率)` 开始、`buzz.off()` 停止；`freq(频率, 时长)`、`stop()` 和内置旋律也可用。最小状态变化程序：

```cpp
#include <MPython.h>

bool wasPressed = false;

void setup() {
  Serial.begin(115200);
  buzz.off();
  Serial.println("STARCORE_BUTTON_BUZZER_READY");
}

void loop() {
  bool pressed = buttonA.isPressed() || buttonB.isPressed();
  if (pressed != wasPressed) {
    wasPressed = pressed;
    if (pressed) {
      buzz.freq(880);
      Serial.println("BUTTON_DOWN");
    } else {
      buzz.off();
      Serial.println("BUTTON_UP");
    }
  }
  delay(10);
}
```

该程序已在当前 Mind+ 1.8 目标编译通过。按键是否触发、蜂鸣器是否发声、音量和音高仍需实体板确认。P5/P11 同时是启动相关脚；上电或复位时一直按住按键可能改变启动状态。

## 掌控板兼容对象的实物边界

当前库还定义了 `display`、`rgb`、`light`、`sound` 和六个 `touchPad*` 对象。对星核板 v4.2.2 必须按下表解释：

| 软件对象 | 星核板实物解释 |
| --- | --- |
| `display` | 板上没有屏幕；需要外接通常为 0x3C 的 OLED |
| `rgb` / `pixels` | 板上没有掌控板的三颗 WS2812；库模型使用 P7/GPIO17 |
| `light` | 只会读 P4/GPIO39；板上没有光线传感器 |
| `sound` | 只会读 P10/GPIO36；板上没有麦克风 |
| `touchPadP/Y/T/H/O/N` | 是 P23-P28 的电容触摸 GPIO 映射，不是六块专用触摸板 |

`mPython.begin()` 会顺带初始化 `display`、P7 像素模型、蜂鸣器和加速度传感器。需要 QMI8658 时应调用它；若项目同时重用 P7 或自定义 I2C 0x3C 设备，要把初始化副作用写进引脚/地址占用表。

## 板载 CAN 物理层

星核板已板载 SIT3051TK 收发器，ESP32 CAN 控制器使用 P13/GPIO18 发送、P14/GPIO19 接收，外部走 CAN_H/CAN_L。当前 Mind+ 1.8 核心提供旧命名的 `driver/can.h`，不是新版 `driver/twai.h`。只读起步应使用 `CAN_MODE_LISTEN_ONLY`，并把实际总线波特率替换成一致值：

```cpp
#include <driver/can.h>

void setup() {
  Serial.begin(115200);
  can_general_config_t general = {};
  general.mode = CAN_MODE_LISTEN_ONLY;
  general.tx_io = GPIO_NUM_18;
  general.rx_io = GPIO_NUM_19;
  general.clkout_io = (gpio_num_t)CAN_IO_UNUSED;
  general.bus_off_io = (gpio_num_t)CAN_IO_UNUSED;
  general.tx_queue_len = 5;
  general.rx_queue_len = 5;
  general.alerts_enabled = CAN_ALERT_NONE;
  general.clkout_divider = 0;
  can_timing_config_t timing = CAN_TIMING_CONFIG_500KBITS();
  can_filter_config_t filter = CAN_FILTER_CONFIG_ACCEPT_ALL();
  if (can_driver_install(&general, &timing, &filter) == ESP_OK &&
      can_start() == ESP_OK) {
    Serial.println("STARCORE_CAN_LISTEN_READY");
  } else {
    Serial.println("STARCORE_CAN_INIT_FAILED");
  }
}

void loop() {
  can_message_t message;
  if (can_receive(&message, pdMS_TO_TICKS(100)) == ESP_OK) {
    Serial.printf("CAN_ID=%lX DLC=%u\n",
                  (unsigned long)message.identifier,
                  message.data_length_code);
  }
}
```

该监听程序已使用当前 Mind+ 1.8 目标编译通过，但尚未接入 CAN 总线。编译不证明波特率、终端电阻、线序、帧 ID、协议或实物通信正确；未知网络不要直接切换正常发送模式。

七个自研模块都先包含 `MPython.h`。在 Mind+ 中按下面的模块编号准备扩展，不要因为外形相似就换成另一套库：

- IDMD-0001 RGB：内置 `ledcSetup`、`ledcAttachPin`、`ledcWrite`；共阳模块需要反相 PWM。
- IDMD-0002 MP3：扩展 `serialMp3`，头文件 `DFRobot_SerialMp3.h`；使用 `serialMp3.begin(&Serial1, P15, P16)`、`volume()`、`playList()`。
- IDMD-0021 OLED：使用 `MPython.h` 自带的全局 `display`；使用 `begin()`、`setCursorLine()`、`printLine()`、`fillInLine()`，不要擅自换成 U8g2。
- IDMS-0001 按钮：内置 `pinMode(P8, INPUT)` 和 `digitalRead(P8)`；按下为 `HIGH`。
- IDMS-0003 电位器：内置 `analogRead(P0)`；先看原始值，不预设旋转方向和满量程。
- IDMS-0008 DHT11：扩展 `dhtTHSensor`，头文件 `DFRobot_DHT.h`；使用 `begin(P0, DHT11)`，温度和湿度交替读取，每次间隔 2500 ms。
- IDMS-0009 超声波：扩展 `sen0001`，头文件 `DFRobot_URM10.h`；使用 `getDistanceCM(P_H, P_O)`，零值按超时或失败处理。

对应的七个完整示例都位于 `examples/chatduino/starcore/` 下，以 Recipe ID 命名：

```text
starcore-idmd-0001-rgb-pwm
starcore-idmd-0002-serial-mp3
starcore-idmd-0021-oled-message
starcore-idms-0001-button-input
starcore-idms-0003-potentiometer-read
starcore-idms-0008-dht11-serial
starcore-idms-0009-ultrasonic-distance
```

这七个示例已在当前 Mind+ 1.8 目标下真实编译通过（7/7）。编译通过只证明源码、板型和库组合能够生成固件；由于目前没有实体板，烧录、串口、重启和物理效果仍为 `unverified`。

另外提供两个课堂 Recipe，继续复用 canonical 通用组件和同一 Mind+ 目标：

```text
starcore-ws2812-classroom-strip        通用 WS2812，P8，低亮度测试
starcore-sg90-safe-position            通用 SG90，P9，小范围测试
```

这两个新增配方的 `code_compiled` 以各自 Recipe 当前状态为准，不沿用上面的 7/7 结论。I2C 扫描、IDMM-0007 只读诊断和 OLED 中文完整模板位于 ChatDuino 聚焦参考卡，不再各建一个 Recipe。IDMD-0021 中文必须使用 `MPython.h` 的全局 `display`。Mind+ 需要另把 `Noto_Sans_CJK_SC_Light16.xbf` 写入 Flash `0x400000`；普通应用上传不证明字库已存在，U8g2 也不是星核板的修复方案。
