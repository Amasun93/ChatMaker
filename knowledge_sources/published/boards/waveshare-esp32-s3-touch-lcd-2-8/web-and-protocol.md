---
schema_version: "1.0"
kind: knowledge-page
stable_id: waveshare-esp32-s3-touch-lcd-2-8-web-and-protocol
board_id: waveshare-esp32-s3-touch-lcd-2-8
section_id: web-and-protocol
source_refs: [source-waveshare-esp32-s3-touch-lcd-2-8-official]
---
# 程序运行时怎么观察

屏幕诊断和计时器在开机输出一次就绪信息。串口助手打开后可主动发送 `?`，分别读取 `CHATMAKER_WAVESHARE_SCREEN_READY` 或 `CHATMAKER_WAVESHARE_TIMER_READY`。ChatMaker 自动观察可在请求文件里配 `serial_probe: "?"` 和对应的 `expected_serial_marker`。屏幕画面、触控和脱离串口助手后的手感，请分别看实物。

V2 倾斜小球平时只在内存记录帧间隔。发送 `D` 取回近期帧数、最大帧间隔和最近一次 IMU 读取状态。在需要判断卡顿时，先玩一段、再打开串口读一次，测试时持续读串口会改变这个现象。

想做网页控制时，先约定网页要发什么、板子要回什么，再分别查看网页和板子。屏幕与触摸的编译记录不包含 Wi-Fi 或浏览器交互的实测。[微雪开发资料](https://docs.waveshare.net/ESP32-S3-Touch-LCD-2.8/Arduino/)
