# 星核板课堂常用输出与舵机

本页只适用于已经确认的 `IDMC-0001 星核板 v4.2.2`。接线前仍要读取板卡和组件的 canonical 卡；WS2812 和 SG90 是通用组件，不因为接到星核板就改成自研模块。

## WS2812 三线灯带

先确认 `5V/GND/DIN`、灯珠数量和箭头方向。箭头必须从 `DIN` 指向后续灯珠。

```text
【先断电】拔掉星核板 USB，也关闭灯带外部 5V 电源。
【引脚占用】P8 用作灯带数据；外部 5V 只给灯带和电平转换器供电。
【按顺序接线】
星核板 P8 → 74AHCT125 A
74AHCT125 Y → 330Ω 电阻 → 灯带 DIN
74AHCT125 /OE → GND
74AHCT125 VCC → 外部 5V
灯带 5V → 外部 5V
灯带 GND → 外部电源 GND → 星核板 GND（必须共地）
【通电前检查】不要接 DOUT；灯带入口并联 500～1000µF 电容，芯片旁加 0.1µF；按约 60mA/灯珠的最坏值并留 30% 余量选电源。不要从 GPIO 或 3V3 给灯带供电，也不要随意把外部 5V 并入 USB 供电中的星核板 5V 轨。
```

完整课堂程序使用 Recipe `starcore-ws2812-classroom-strip`。先保持低亮度和少量灯珠，实物确认后再扩大数量。

## 普通三线 PWM 舵机

先从丝印或产品资料确认信号、电源和地；棕/红/橙等颜色只能作为线索。

```text
【先断电】拔掉星核板 USB，也关闭舵机外部 5V 电源。
【引脚占用】P9 用作 PWM 控制信号。
【按顺序接线】
舵机 SIGNAL → 星核板 P9
舵机 V+ → 独立且足量的 5V 电源
舵机 GND → 外部电源 GND → 星核板 GND（必须共地）
【通电前检查】摇臂先离开夹手或碰撞位置；不能从 GPIO 或 3V3 给舵机供电。第一次只测试 60°、90°、120°的小范围，机构限位比程序角度优先。
```

完整课堂程序使用 Recipe `starcore-sg90-safe-position`。程序上电先到 `SAFE_ANGLE`，只变化一次，不在 `loop()` 中反复发送相同角度。

## IDMM-0007 串口舵机驱动

IDMM-0007 不是普通三线 PWM 舵机。先确认驱动板编号、所配舵机品牌和型号、供电范围、UART 电平、波特率、舵机 ID、帧格式和校验方式。缺少任意协议资料时，不能生成试转、扫描 ID、复位或运动命令。

```text
【先断电】拔掉 USB，关闭驱动板和舵机动力电源。
【引脚占用】只读诊断只占用 P26（主控 RX）；P23 暂不连接。
【按顺序接线】
IDMM-0007 TXD → 星核板 P26（只接收）
IDMM-0007 GND → 星核板 GND
IDMM-0007 RXD → 暂不连接
IDMM-0007 VCC/动力电源 → 先按对应驱动与舵机资料确认，资料不明时不要通电
【通电前检查】确认 UART 逻辑电平不超过 3.3V。只运行下面的接收模板；代码不得出现 `ServoBus.write()`、`ServoBus.print()` 或任何运动帧。
```

```cpp
#include <MPython.h>

const unsigned long MONITOR_BAUD = 9600;  // 观察起点，不代表协议已确认。
HardwareSerial ServoBus(1);

void setup() {
  Serial.begin(115200);
  ServoBus.begin(MONITOR_BAUD, SERIAL_8N1, P26, P23);
  Serial.println("IDMM0007_RX_ONLY_READY");
  Serial.println("NO_MOTION_COMMAND_WILL_BE_SENT");
}

void loop() {
  while (ServoBus.available()) {
    Serial.printf("%02X ", ServoBus.read());
  }
}
```

只读程序没有收到数据并不能证明模块损坏，很多舵机总线不会主动发送。只有拿到准确协议后，才能另建受范围、校验、急停和机械限位保护的运动项目。
