---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-c6-devkitc-1-troubleshooting
board_id: esp32-c6-devkitc-1
section_id: troubleshooting
source_refs: [source-esp32-c6-devkitc-1-official]
---
# 课堂常见问题和排错

- **两个 Type-C 都能插，选哪个？** 首次诊断只接 USB 转串口，并选择 `uart`。要切到原生 USB 时，改用另一个插口、`native` 参数和它新出现的端口。
- **有电源灯，却完全看不到串口？** 换一根已确认能传数据的 USB 线，绕开集线器。转串口有系统设备、无串口时，按这个转换芯片查驱动。检查是否为了测量电流动过 J5 跳线。
- **烧录成功后，原来的原生串口不见了？** 刷新列表选程序端口。如果还没有，检查代码是否重新配置了原生 USB 的引脚或让板子睡眠。先关串口监视器，再按住 BOOT、点按并松开 RESET、松开 BOOT，之后重选端口。也可以按 `uart` 模式重新编译，通过转串口诊断。
- **Windows 编译报 `compiler_path_too_long`？** 若报错还提到 `bits/c++config.h` 或 `bits/error_constants.h`，可用 Windows 安装入口的 `-RuntimeRoot` 将运行时准备到较短的本地目录，再准备和编译本板。
- **彩灯一直没变化？** 先查串口是否持续打印，再核对用的是可寻址 RGB 驱动和实际 GPIO。给老师的记录带上板型及版本、插口、端口、报错全文与最后一项成功的观察。

[乐鑫 C6 烧录排错](https://docs.espressif.com/projects/esptool/en/latest/esp32c6/troubleshooting.html) · [原生 USB 串口限制和恢复](https://docs.espressif.com/projects/esp-idf/en/v5.5.6/esp32c6/api-guides/usb-serial-jtag-console.html)
