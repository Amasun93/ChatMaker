---
schema_version: "1.0"
kind: knowledge-page
stable_id: waveshare-esp32-s3-touch-lcd-2-8-web-and-protocol
board_id: waveshare-esp32-s3-touch-lcd-2-8
section_id: web-and-protocol
source_refs: [source-waveshare-esp32-s3-touch-lcd-2-8-official]
---
# 程序运行时怎么观察

可先接 USB 数据线，用串口看板子发出的文字。屏幕诊断会反复输出 `CHATMAKER_WAVESHARE_SCREEN_READY`。课堂计时器会输出 `CHATMAKER_WAVESHARE_TIMER_READY` 和触摸事件。读到文字可以核对程序是否运行。屏幕画面和触控是否有效，请分别看实物。

想做网页控制时，先约定网页要发什么、板子要回什么，再分别查看网页和板子。屏幕与触摸的编译记录不包含 Wi-Fi 或浏览器交互的实测。[微雪开发资料](https://docs.waveshare.net/ESP32-S3-Touch-LCD-2.8/Arduino/)
