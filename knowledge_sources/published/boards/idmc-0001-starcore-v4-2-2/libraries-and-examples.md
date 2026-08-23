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
