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

先读取 canonical board `idmc-0001-starcore-v4-2-2`，确认用户手里是 IDMC-0001 星核板 v4.2.2。软件里选择兼容的掌控板目标只代表复用软件生态，物理接线仍以星核板丝印和本知识为准。

v4.2.2 已板载 QMI8658 六轴惯性传感器，可直接读取三轴加速度、合加速度和倾斜/摇晃手势。体感项目先读取 `libraries-and-examples`：Mind+ 掌控板模式有现成加速度积木，Arduino/C++ 使用 `MPython.h` 的全局 `accelerometer`。不要让用户再确认芯片型号，不要要求外接加速度模块，也不要从手写 I2C 驱动开始。

按目标进入对应路线：编程与接线使用 ChatDuino；网页交互先定义消息协议后交给 ChatWeb；安装底板或外壳使用 ChatCAD，并读取 `knowledge/mechanical/boards/idmc-0001-starcore-v4-2-2.json`。机械资料来自清洗后的尺寸，不包含制造源文件，实体装配仍是 `unverified`。

环境发现、代码生成、编译、上传、串口输出、网络交互和真实效果必须分别报告。现有源资料中的历史验证不能自动证明当前电脑、当前板卡或当前项目已经通过。
