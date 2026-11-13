# ChatMaker 在 macOS 上的 WorkBuddy 复测

从 ChatMaker 源码目录运行。Apple 芯片和 Intel Mac 各有对应的工具包。需要 Git、Python 3.11 或更高版本，以及能运行本地命令的 WorkBuddy。Apple 芯片的 Mac 需要 Rosetta 来运行当前固定版本的 Arduino 辅助工具和 AVR 编译器。[Apple 的 Rosetta 安装说明](https://support.apple.com/102527)

## 确认复测版本并准备环境

在 Mac 的 ChatMaker 目录执行以下命令。将最后一行的 `FULL_COMMIT_SHA` 替换为本次交付的完整提交号。

```bash
git status --short
git rev-parse HEAD
bash scripts/setup_local_runtime.sh --check-only
bash scripts/setup_local_runtime.sh
python3 scripts/workbuddy_preflight.py --expected-revision FULL_COMMIT_SHA
```

预检返回 `success: true` 后继续。它会核对源码目录、完整提交号、工作区状态、安装版本和本地 Python。若电脑安装了多个 Python，可在运行安装脚本时通过 `CHATMAKER_PYTHON` 指定所需的解释器路径。

```bash
CM="$PWD/.chatmaker-runtime/bin/chatmaker-hardware"
```

## 选择实际板型

| 开发板 | `--board-id` | 选项 |
| --- | --- | --- |
| Arduino Uno R3 | `arduino-uno-r3` | ATmega328P |
| 经典 Arduino Nano | `arduino-nano-classic` | ATmega328P。已知时可指定 `--bootloader new` 或 `--bootloader old` |
| Arduino Mega 2560 | `arduino-mega-2560` | ATmega2560 |
| DOIT ESP32 DEVKIT V1 | `esp32-devkit-v1` | ESP-WROOM-32 |
| Nova 经典 ESP32 | `nova-esp32` | 已核对的 4 MB 配置 |
| Espressif ESP32-C3-DevKitM-1 | `esp32-c3-devkitm-1` | 4 MB，板载 USB 转串口 |
| Espressif ESP32-C6-DevKitC-1 | `esp32-c6-devkitc-1` | 8 MB，按使用的插口选择 `--usb-mode uart` 或 `--usb-mode native` |
| Espressif ESP32-S3-DevKitC-1 | `esp32-s3-devkitc-1-n8r8` | N8R8，按使用的插口选择 `--usb-mode uart` 或 `--usb-mode native` |
| 微雪 ESP32-S3-Touch-LCD-2.8 | `waveshare-esp32-s3-touch-lcd-2-8` | 以背面标签为准，选 `--revision v1` 或 `--revision v2` |

经典 Nano 引导程序未知时，可以让下载流程先尝试新版。只有出现引导程序同步失败并仍能匹配原串口设备时，才尝试旧版。新项目使用标准 Arduino 核心及其库。已有代码如果引用 Mind+ 附带的 `DFRobot_*` 库，需要对应库源码或按项目改用标准库。

## Arduino Uno R3 闪灯复测

```bash
BOARD=arduino-uno-r3
SKETCH="$PWD/examples/chatduino/uno/blink"
"$CM" --action prepare-environment --board-id "$BOARD" --dry-run
"$CM" --action prepare-environment --board-id "$BOARD"
"$CM" --action compile --board-id "$BOARD" --sketch "$SKETCH"
"$CM" --action ports --board-id "$BOARD"
```

确认实物和端口后，在下面命令中填入返回的 `/dev/cu.*` 地址，保持大小写。连接多个串口设备时，明确选中本次要写入的板子。

```bash
"$CM" --action run --board-id "$BOARD" --sketch "$SKETCH" \
  --board-confirmed --port /dev/cu.usbmodemXXXX
```

## 微雪触屏复测

以下命令以 V1 为例。背面写 V2 时改用 `v2`。

```bash
BOARD=waveshare-esp32-s3-touch-lcd-2-8
REV=v1
SKETCH="$PWD/examples/chatduino/waveshare-s3/classroom-timer"
"$CM" --action prepare-environment --board-id "$BOARD" --revision "$REV"
"$CM" --action compile --board-id "$BOARD" --revision "$REV" --sketch "$SKETCH"
"$CM" --action ports --board-id "$BOARD" --revision "$REV"
"$CM" --action run --board-id "$BOARD" --revision "$REV" --sketch "$SKETCH" \
  --board-confirmed --port /dev/cu.usbmodemXXXX
```

运行后观察屏幕和 START、PAUSE、RESET 触控，再检查断电重启。需要串口运行证据时，用 JSON 请求文件设置 `expected_serial_marker` 为 `CHATMAKER_WAVESHARE_TIMER_READY`，并用 `--request-file` 传给同一个入口。

## 回传记录

- 保存预检 JSON、Mac 芯片架构、macOS 版本和板上印字。
- 记录首次准备耗时、来源、是否使用已有缓存，以及第二次是否再次下载。ESP32 大组件优先走乐鑫国内地址。Arduino 的部分小工具使用官方直连地址。
- 记录具体 USB 口、端口地址、编译结果、烧录结果和实际效果。Mac 编译任务可验证固件产物。烧录、串口、触摸和重启由接板实测确认。
