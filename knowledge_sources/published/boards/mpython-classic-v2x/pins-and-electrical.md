---
schema_version: "1.0"
kind: knowledge-page
stable_id: mpython-classic-v2x-pins-and-electrical
board_id: mpython-classic-v2x
section_id: pins-and-electrical
source_refs: [source-mpython-classic-v2x-official]
---
# 使用经典版引脚表

P19/GPIO22 是 SCL，P20/GPIO23 是 SDA，二者已连接板载 OLED 和运动/磁场传感器，外接 I2C 模块前先检查地址冲突。P2、P3、P4、P10 是输入专用脚，不能驱动 LED、蜂鸣器或执行器。P5、P11 连接 A/B 键并涉及启动状态。

引脚编号不能复制掌控板 3.0：3.0 的 P19/P20 已变为 GPIO43/GPIO44。完整映射和约束以板卡记录 `mpython-classic-v2x` 为准。

