---
schema_version: "1.0"
kind: knowledge-page
stable_id: stardust-atmega328p-web-and-protocol
board_id: stardust-atmega328p
section_id: web-and-protocol
source_refs: [source-stardust-atmega328p-observed]
---
# 需要联网交互时再定义协议

当前星辰板闭环只验证 USB 串口输出，没有登记 Wi-Fi 或蓝牙能力。若未来由网页控制，应先选择外部通信模块并定义命令、响应、超时和安全边界，不根据 ATmega328P 或 CH340 猜测网络功能。
