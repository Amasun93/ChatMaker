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
- V2 倾斜小球使用 `examples/chatduino/waveshare-s3/v2-tilt-dot`，直接画到 ST7789，从 QMI8658 读取倾斜。它是可单独编译和复测的起点；平衡球完整作品、校准存储和碰撞音效各有自己的验证范围。

编译准备会从已校验的微雪对应版本归档中提取板卡驱动和 LVGL 8.3.10。V2 的官方压缩包里有 CST3530 源码，部分示例回调仍接向 V1 的驱动。ChatMaker 在本机准备的副本里将 V2 的回调接到 CST3530，以匹配实物版本。

V2 还会从同一个归档准备 `WaveshareMotion`，提供 `Gyro_QMI8658.h` 和 `I2C_Driver.h`。使用原生 I²S 时可包含 Arduino-ESP32 核心的 `ESP_I2S.h`。板载 PCM5101 的 BCLK 是 GPIO48，WS 是 GPIO38，DOUT 是 GPIO47。官方 `Audio_PCM5101` 示例依赖另外的音频和 SD 库，官方全功能示例、RTC 和 SD 驱动需要按作品单独确认。

用 `doctor` 查看 `peripheral_coverage`，用 `ready_for_compile` 判断本机是否已经准备好。编译通过后的屏幕、触摸、IMU 和实际发声分别观察。驱动出现在官方 ZIP，以及音频测试指令得到响应，是两种不同的证据。[微雪 V2 示例包](https://docs.waveshare.net/ESP32-S3-Touch-LCD-2.8/Resources-And-Documents/) · [Issue #6](https://github.com/Amasun93/ChatMaker/issues/6)
