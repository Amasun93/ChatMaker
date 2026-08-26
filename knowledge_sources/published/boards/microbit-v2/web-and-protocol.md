---
schema_version: "1.0"
kind: knowledge-page
stable_id: microbit-v2-web-and-protocol
board_id: microbit-v2
section_id: web-and-protocol
source_refs: [source-microbit-v2-official]
---
# 需要交互时再确定通信方式

USB 串口可作为本地电脑与程序的简单通信入口；当前计划速率为 115200，但仍待实板观察。蓝牙或浏览器项目需要根据运行环境单独选择官方支持的方案，不能仅凭板卡有蓝牙就假定网页能直接连接。

任何交互都应先定义命令、响应、超时、重连和安全边界，再分别验证网页端、通信链和实体效果。
