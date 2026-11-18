---
schema_version: "1.0"
kind: knowledge-page
stable_id: waveshare-esp32-s3-touch-lcd-2-8-pins-and-electrical
board_id: waveshare-esp32-s3-touch-lcd-2-8
section_id: pins-and-electrical
source_refs: [source-waveshare-esp32-s3-touch-lcd-2-8-official]
---
# 想接外部模块时看这里

先核对板子上印的字和模块的电压。当前数据表见 `packs/boards/waveshare-esp32-s3-touch-lcd-2-8.yaml`。

- 外接两线接口 I²C 用 `SDA → GPIO11`、`SCL → GPIO10`。这里与板上器件共用，接新模块前检查电压与地址。
- 触摸屏内部也用两线通信，走内部的 `GPIO1` 和 `GPIO3`，复位和中断用 `GPIO2` 和 `GPIO4`。
- 板载屏幕占用 `GPIO45/40/42/41/39/5`。USB 通信占用 `GPIO19/20`。预留这些脚给原有用途。
- 考虑外接普通信号时，先从板卡记录中核对 `GPIO15`、`GPIO18`，看是否已被当前作品用掉。

没有认清接口丝印或模块供电要求时，先确认那项再接线。[微雪原理图入口](https://docs.waveshare.net/ESP32-S3-Touch-LCD-2.8/Resources-And-Documents/)
