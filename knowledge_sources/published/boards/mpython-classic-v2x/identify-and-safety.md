---
schema_version: "1.0"
kind: knowledge-page
stable_id: mpython-classic-v2x-identify-and-safety
board_id: mpython-classic-v2x
section_id: identify-and-safety
source_refs: [source-mpython-classic-v2x-official]
---
# 自动识别不靠猜

USB 串口芯片、ESP32 或 QMI8658 只能作为线索。优先读取已有 ChatMaker 身份标记；需要临时探针时，必须先完整备份并验证原固件，探测后恢复并再次验证。若结果仍可能属于多个板型，引导用户查看背面版本丝印；仍不清楚时请用户拍清晰的正反面照片。

经典板使用 3.3V 逻辑。接线前断开 USB 和外部电源，不把 5V 信号直接接入 GPIO。V2.0 使用 MSA300，V2.1 起使用 QMI8658C，V2.2 起更换磁传感器；V2.3 的部分文档差异属于 API 行为，不能在缺少硬件证据时猜版本。

