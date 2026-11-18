---
schema_version: "1.0"
kind: knowledge-page
stable_id: unihiker-m10-pins-and-electrical
board_id: unihiker-m10
section_id: pins-and-electrical
source_refs: [source-unihiker-m10-official]
---
# 外设接线前，先看引脚图

1. 在 ChatMaker 板卡条目中选 `unihiker-m10`。看官方 M10 正面引脚图时，先把手中板子和图转到同一方向。厂商说明背面的金手指没有电气连接。 [M10 引脚与原理图](https://www.unihiker.com/wiki/HardwareReference/hardware_reference_board_overview/)
2. 根据模块资料核对电源、地和每一根信号线。三针接口要查清选的是数字、模拟还是 PWM 功能。四针 I²C 模块要核对供电、地、SDA 和 SCL，再确认该模块的地址与所用接口对应。接头的外形和线的颜色只能用于辅助识别。 [M10 硬件与接口功能](https://www.unihiker.com.cn/wiki/m10/jianjie) · [PinPong 通信用法](https://www.unihiker.com/wiki/LanguageReference/PinPong_Library/)
3. 供电允许值和信号允许值要分别确认。即使模块可以用更高的电压供电，也应先核对它输出的信号电平。信号超出 M10 引脚允许值时，先选匹配的电平转换方案。普通单端信号需要共地。 [M10 供电与工作电压](https://www.unihiker.com.cn/wiki/m10/jianjie)
4. 断电接一个模块，再上电跑它自己的读取或控制示例。能观察到正确的效果之后，再接下一个。I²C 读不到时，先对照接口和地址，再看接线和初始化。
