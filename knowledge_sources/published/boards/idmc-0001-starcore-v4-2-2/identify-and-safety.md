---
schema_version: "1.0"
kind: knowledge-page
stable_id: idmc-0001-starcore-v4-2-2-identify-and-safety
board_id: idmc-0001-starcore-v4-2-2
section_id: identify-and-safety
source_refs:
  - source-idmc-0001-starcore-v4-2-2-owned-docs
---
# 识别板卡并先保证安全

确认主控丝印、版本和 USB 数据连接，不要只凭外形判断。普通三线接口从上到下是 `S / V / G`，分别代表信号、电源和地；俯视接线图里叠在同一位置的三种线色不是三个信号引脚。四线 I2C、UART 和超声波接口必须按模块与板卡的同名丝印核对。

ESP32 GPIO 的输入逻辑上限是 3.3V。模块使用 5V 供电，不等于它的信号输出可以直接进入 GPIO。电机、舵机、灯带等大电流负载使用足量外部电源并与星核板共地，不能从 GPIO 或 3.3V 引脚取得动力电源。接线和改线时先断电，首次上电一次只接一个模块。

PD 电源模块、电机驱动和未知批次传感器都需要先测量实际电压。任何未测量的供电或接口差异都保持 `unverified`，不能用“通常如此”代替确认。
