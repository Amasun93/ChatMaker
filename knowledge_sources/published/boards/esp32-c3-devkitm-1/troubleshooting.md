---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-c3-devkitm-1-troubleshooting
board_id: esp32-c3-devkitm-1
section_id: troubleshooting
source_refs: [source-esp32-c3-devkitm-1-official]
---
# 课堂常见问题和排错

- **电源灯亮，为什么没有串口？** 换已知可传数据的 Micro-USB 线，直接插电脑并刷新端口列表。若系统设备列表有插拔变化却无串口，再查板载 USB 转串口芯片对应的驱动。
- **有端口，为什么一直连接失败？** 关闭占用串口的监视器。先拔掉外接线，按住 BOOT，点按并松开 RESET，最后松开 BOOT，再试写入。完成后松开 BOOT 并重启，观察程序。
- **编译提示找不到 `bits/c++config.h` 或 `bits/error_constants.h`？** 在 Windows 上出现 `compiler_path_too_long` 时，把 ChatMaker 运行时准备到更短的本地目录，例如使用 Windows 源码安装入口的 `-RuntimeRoot`，再从新目录运行板型准备和编译。
- **写入成功，为什么只有一盏灯常亮？** 常亮的可能是供电指示灯。先通过串口确认程序起来，再核对程序是否用可寻址彩灯的驱动，以及数据脚是否与板卡记录一致。
- **怎样回报做到了哪一步？** 带上板卡正反面照片、操作系统、端口、报错原文、草图路径，以及最后成功的一步。编译、写入、串口输出、彩灯效果和拔线重启分别记录。

[乐鑫 C3 下载模式](https://docs.espressif.com/projects/esptool/en/latest/esp32c3/advanced-topics/boot-mode-selection.html) · [乐鑫板卡手册](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32c3/esp32-c3-devkitm-1/user_guide.html)
