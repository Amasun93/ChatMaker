---
schema_version: "1.0"
kind: knowledge-page
stable_id: waveshare-esp32-s3-touch-lcd-2-8-identify-and-safety
board_id: waveshare-esp32-s3-touch-lcd-2-8
section_id: identify-and-safety
source_refs: [source-waveshare-esp32-s3-touch-lcd-2-8-official]
---
# 先确认板子

请看板子背面的产品名和版本。知道完整型号和 V2 就可以采用 CST3530 路线。`ESP32-S3` 芯片名、电脑上的 COM 口和新购买的时间都不足以判定板子的版本。只有控制器名时，继续核对完整板型。运行烧录前，还需确认对应的实物和 USB 端口。

改接线前拔掉 USB 和外接供电。GPIO 使用 3.3 V 信号。5 V 输出需要先确认如何转换电平。连接电脑时用支持传数据的 USB 线。[微雪相关资料和原理图入口](https://docs.waveshare.net/ESP32-S3-Touch-LCD-2.8/Resources-And-Documents/)
