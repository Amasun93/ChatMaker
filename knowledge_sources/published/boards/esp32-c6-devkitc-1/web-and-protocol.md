---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-c6-devkitc-1-web-and-protocol
board_id: esp32-c6-devkitc-1
section_id: web-and-protocol
source_refs: [source-esp32-c6-devkitc-1-official]
---
# 串口、网页和通信

电脑串口监视器要选实际插口对应的端口。转串口用草图的波特率，原生 USB 路线上要留意重启后新出现的程序端口。先打印一行可识别的运行状态。

手机网页可先通过 2.4 GHz Wi-Fi 测试局域网访问，也可以连板自己开的热点。以串口实际打印出来的 IP 打开页面。学校 Wi-Fi 如果把设备彼此隔离，先用板载热点测试页面访问，再检查学校网络。经典 ESP32 的 `esp32-ap-led-sensor` 可用来参考网页怎么向板子发消息，接线和引脚要按 C6 重新定。

C6 还支持 Zigbee、Thread 和 BLE。要接指定生态的设备，先查对方要求的协议、角色和网关，再选对应软件与示例。跑通 Wi-Fi 网页只说明当前的 Wi-Fi 路线已观察到结果。

[乐鑫 v1.2 通信能力](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32c6/esp32-c6-devkitc-1/user_guide.html#description-of-components) · [Arduino Wi-Fi 接口](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/wifi.html)
