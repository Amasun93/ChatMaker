---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-c3-devkitm-1-web-and-protocol
board_id: esp32-c3-devkitm-1
section_id: web-and-protocol
source_refs: [source-esp32-c3-devkitm-1-official]
---
# 串口、网页和通信

用 USB 转串口接电脑，选择插线时刚出现的端口。串口监视器的波特率跟着草图设置，例如草图用 `Serial.begin(115200)`，监视器也用 115200。多次发送同一条信息，打开监视器晚一点也有机会看到。

做手机网页时，先让手机与板在同一个可互访的 2.4 GHz Wi-Fi 网络，或让手机加入板自己开的热点。以串口打印的 IP 为准，访问浏览器里的 `http://` 地址。先让页面显示一条状态，再加输入或控制。看到页面、收到 HTTP 响应、外设执行是三次不同的观察。

`esp32-ap-led-sensor` 可以用来理解网页与板卡如何通信。它是经典 ESP32 的配方，选脚和传感器线路应按当前 C3 重新核对，重新编译和实测。

[乐鑫 Arduino Wi-Fi 接口](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/wifi.html)
