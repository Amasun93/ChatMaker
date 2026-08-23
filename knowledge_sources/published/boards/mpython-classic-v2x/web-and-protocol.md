---
schema_version: "1.0"
kind: knowledge-page
stable_id: mpython-classic-v2x-web-and-protocol
board_id: mpython-classic-v2x
section_id: web-and-protocol
source_refs: [source-mpython-classic-v2x-official]
---
# 网页联动先定义消息

经典掌控板可以通过 USB 串口或 Wi-Fi 与网页配合。先定义消息名称、字段、单位、刷新频率和断线行为，再分别实现板端与网页端。串口出现文本只证明通信线索；网页收到数据、传感器读数合理和实体效果发生仍是不同验证阶段。

不要把模拟数据按钮当成真实硬件连接，也不要因程序能编译就报告网页已经控制了板子。

