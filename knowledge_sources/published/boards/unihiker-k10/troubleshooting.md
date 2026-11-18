---
schema_version: '1.0'
kind: knowledge-page
stable_id: unihiker-k10-troubleshooting
board_id: unihiker-k10
section_id: troubleshooting
source_refs:
- source-unihiker-k10-official
---
# DFRobot UNIHIKER K10 行空板｜课堂常见问题和排错

- 端口没有出现 → 换数据线，再按背面 BOOT 与 RESET 进入下载模式，选随 K10 出现的端口。
- 准备工具比较慢 → 看当前下载的是 K10 核心还是编译器，保留可续传的文件。
- 代码写入后看不到旧菜单 → 三灯例子只负责彩灯和串口。需要旧菜单时用 DFRobot 出厂程序恢复。
- 外接模块后内置传感器一起异常 → 先断开外接模块，检查供电、方向和 I²C 地址。

[DFRobot 出厂程序](https://www.unihiker.com.cn/wiki/k10/default-program)

[ChatMaker 本轮验证与复测](https://github.com/Amasun93/ChatMaker/blob/main/docs/verification/2026-11-18-classroom-boards.md)
