---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-s3-devkitc-1-n8r8-troubleshooting
board_id: esp32-s3-devkitc-1-n8r8
section_id: troubleshooting
source_refs: [source-esp32-s3-devkitc-1-n8r8-official]
---
# 课堂常见问题和排错

- **USB 灯亮，为什么找不到端口？** 换一根确认能传数据的 Micro-USB 线，用 USB-to-UART 插口先诊断。刷新端口列表。如果有新设备却无串口，查相应的转接芯片驱动。
- **能看到串口，但连接失败？** 关闭串口监视器，先拿掉外接线。按住 BOOT、点按并松开 RESET、再松开 BOOT，重新查看端口。原生 USB 下烧录后若端口变化，再选择程序端口。
- **程序有串口输出，彩灯没反应？** 确认看到的是可编程彩灯，检查载板版本对应的数据脚，以及草图是否用 `rgbLedWrite` 发送颜色。
- **反复重启，或日志报 PSRAM 初始化失败？** 先读清金属罩和包装上的商品后缀，确认目标是 `N8R8` 和对应的八线 PSRAM 配置。用只打印状态的草图复测，随后逐个加回外设。
- **课堂验收要记录什么？** 附板子和模块照片、载板版本、USB 口与操作系统端口，以及最后成功的一项。编译、写入、串口、彩灯或外设、断电重启分别记录。

[乐鑫 S3 启动模式](https://docs.espressif.com/projects/esptool/en/latest/esp32s3/advanced-topics/boot-mode-selection.html) · [乐鑫 Arduino-ESP32 Flash/PSRAM 排错](https://docs.espressif.com/projects/arduino-esp32/en/latest/troubleshooting.html)
