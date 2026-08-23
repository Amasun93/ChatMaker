---
schema_version: "1.0"
kind: knowledge-page
stable_id: idmc-0001-starcore-v4-2-2-start-here
board_id: idmc-0001-starcore-v4-2-2
section_id: start-here
source_refs:
  - source-idmc-0001-starcore-v4-2-2-owned-docs
---
# 星核板从这里开始

先读取 canonical board `idmc-0001-starcore-v4-2-2`，确认用户手里是 IDMC-0001 星核板 v4.2.2。可从正面 `星核板 / V4.2.2 / 斯坦星球 / IDEALAB` 丝印、USB-C、CAN BUS、两颗按键和三排 S/V/G 接口辨认。软件里选择兼容的“掌控板”目标只代表复用软件生态，物理接线仍以星核板丝印和本知识为准。

## 先知道板上真正有什么

v4.2.2 实物已确认板载 A/B 按键、无源蜂鸣器、QMI8658 六轴惯性传感器、CH9102F USB 串口桥、SIT3051TK CAN 收发器，以及 3.3V/5V I2C 接口和多档电源入口。QMI8658 可通过当前 `MPython.h` 读取三轴加速度、合加速度和倾斜/摇晃手势；按键使用 `buttonA/buttonB`，蜂鸣器使用 `buzz`。

体感项目直接读取 `libraries-and-examples`：Mind+ 掌控板模式有现成加速度积木，Arduino/C++ 使用 `mPython.begin()` 和全局 `accelerometer`。不要让用户再确认加速度芯片，不要要求外接 LIS2DH12，也不要从手写 I2C 驱动开始。QMI8658 芯片虽含陀螺仪，但当前已审查的 `MPython.h` 没有公开陀螺仪读数 API；没有另行验证驱动前，不能承诺可直接读角速度。

## 掌控板积木不等于星核板实物

`MPython.h` 同时暴露 `display`、`rgb`、`light` 和 `sound`，但星核板 v4.2.2 实物没有板载屏幕、三颗 WS2812、光线传感器或麦克风。这些对象只是兼容软件模型：

- `display` 需要外接 0x3C OLED；
- `rgb` 使用 P7/GPIO17 的掌控板三像素模型，但星核板没有板载像素；
- `light.read()` 实际读 P4/GPIO39，`sound.read()` 实际读 P10/GPIO36；未外接传感器时不代表真实光线或声音；
- `touchPadP/Y/T/H/O/N` 对应可触摸 GPIO，并不代表 PCB 上另有六块专用触摸区。

`mPython.begin()` 会初始化 0x3C 显示对象和 P7 的 WS2812 模型。若项目要把 P7 当普通 GPIO，或 I2C 上已有 0x3C 设备，必须先检查这两个初始化副作用。

按目标进入对应路线：编程与接线使用 ChatDuino；引脚和电源先读 `identify-and-safety` 与 `pins-and-electrical`；网页交互先定义消息协议后交给 ChatWeb；安装底板或外壳使用 ChatCAD，并读取 `knowledge/mechanical/boards/idmc-0001-starcore-v4-2-2.json`。机械资料来自清洗后的尺寸，不包含制造源文件，实体装配仍是 `unverified`。

环境发现、代码生成、编译、上传、串口输出、网络交互和真实效果必须分别报告。现有源资料中的历史验证不能自动证明当前电脑、当前板卡或当前项目已经通过。
