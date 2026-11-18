---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-s3-devkitc-1-n8r8-web-and-protocol
board_id: esp32-s3-devkitc-1-n8r8
section_id: web-and-protocol
source_refs: [source-esp32-s3-devkitc-1-n8r8-official]
---
# 串口、网页和通信

串口读哪一个端口，由接线和编译时的 USB 模式共同决定。USB-to-UART 用草图写的波特率。原生 USB 在程序启动时可能出现新的地址。先让程序定期输出状态，再开串口监视器观察。

网页项目可先让电脑或手机与开发板连到可互访的 2.4 GHz Wi-Fi，或让手机连板自己开的热点。通过串口查 IP，然后打开 `http://` 地址。先验收页面出现，再验收发送命令后板上的可见效果。这里的 Wi-Fi 网页和 S3 的原生 USB 是两条不同的通路。

经典 ESP32 的 `esp32-ap-led-sensor` 可以参考交互步骤。S3 项目重新选 GPIO、核对电压以后再做自己的测试。

[乐鑫 Arduino Wi-Fi 接口](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/wifi.html) · [S3 原生 USB 串口指南](https://docs.espressif.com/projects/esp-idf/en/v5.5.1/esp32s3/api-guides/usb-serial-jtag-console.html)
