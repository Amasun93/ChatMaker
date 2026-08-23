---
schema_version: "1.0"
kind: knowledge-page
stable_id: mpython-v3-identify-and-safety
board_id: mpython-v3
section_id: identify-and-safety
source_refs: [source-mpython-v3-official]
---
# 用组合证据识别 3.0

ESP32-S3 是强线索，但不是唯一身份。继续核对彩色屏、QMI8658C、MMC5603NJ、LTR-308ALS-01、双麦克风和板载扬声器。临时识别程序只有在完整备份并验证原 Flash 后才能写入，探测后必须恢复；工具链未安装时转为丝印或照片识别，不使用经典版程序硬刷。

板卡使用 3.3V 逻辑，USB 或金手指供电方式必须符合官方范围。接线和改线先断电，大电流负载使用独立电源并共地。

