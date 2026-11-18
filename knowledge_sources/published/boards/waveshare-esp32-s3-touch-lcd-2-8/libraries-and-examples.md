---
schema_version: "1.0"
kind: knowledge-page
stable_id: waveshare-esp32-s3-touch-lcd-2-8-libraries-and-examples
board_id: waveshare-esp32-s3-touch-lcd-2-8
section_id: libraries-and-examples
source_refs: [source-waveshare-esp32-s3-touch-lcd-2-8-official]
---
# 示例先跑哪一个

- 屏幕诊断使用 `examples/chatduino/waveshare-s3/screen-diagnostic`，看屏幕是否显示状态和色块。
- 课堂计时器使用 `examples/chatduino/waveshare-s3/classroom-timer`，分别点 START、PAUSE、RESET，再断电重新接上确认还会启动。

编译准备会从已校验的微雪对应版本归档中提取板卡驱动和 LVGL 8.3.10。V2 的官方压缩包里有 CST3530 源码，部分示例回调仍接向 V1 的驱动。ChatMaker 在本机准备的副本里将 V2 的回调接到 CST3530，以匹配实物版本。

两份示例在 V1 和 V2 都有编译记录。触摸、中文字体和其他示例各有自己的验证范围。[微雪示例包](https://docs.waveshare.net/ESP32-S3-Touch-LCD-2.8/Resources-And-Documents/)
