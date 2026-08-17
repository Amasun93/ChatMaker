---
schema_version: "1.0"
kind: knowledge-page
stable_id: idmc-0001-starcore-v4-2-2-pins-and-electrical
board_id: idmc-0001-starcore-v4-2-2
section_id: pins-and-electrical
source_refs:
  - source-idmc-0001-starcore-v4-2-2-owned-docs
---
# 引脚选择规则

先读取 canonical board 中的引脚能力，再分配模块。P0、P1 适合通用模拟或数字输入；P2、P3 只能输入，不能驱动 LED、触发脚或执行器。P13、P14、P15 可作为常用数字或 PWM 端口。P5、P11、P16、P25、P27、P28 与启动状态相关，外设上电时强拉这些端口可能导致无法启动或上传。

星核板信号板有三组 3.3V 和三组 5V 的四针 I2C 接口，它们共享同一条 SCL/SDA 总线。给学生的接线说明优先写“整体插入匹配电压的空闲 I2C 接口”，不要求逐根寻找 P19/P20；但在程序的引脚占用表中仍要保留 P19/P20，避免重复分配。

多模块项目先列引脚占用表，再检查输入输出方向、板载功能、启动敏感端口、I2C 地址和电源电流。模拟传感器先输出原始值并现场校准阈值，不把一个固定阈值当成所有模块和环境的通用事实。
