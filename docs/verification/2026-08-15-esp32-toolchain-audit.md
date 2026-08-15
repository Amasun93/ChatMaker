# ESP32 DevKit V1 工具链审计

## 精确目标

本轮把原先混写的“ESP32 DevKit V1 / ESP-WROOM-32”拆成两个身份层：

```text
载板：DOIT ESP32 DEVKIT V1
模块：ESP-WROOM-32
Profile: doit-esp32-devkit-v1-wroom32
官方 Core: esp32:esp32 3.3.11
FQBN: esp32:esp32:esp32doit-devkit-v1
```

`ESP-WROOM-32` 只是模块丝印，不能单独证明载板。ESP32 Dev Module、Espressif DevKitC、FireBeetle、mPython、C3、S2 和 S3 都不能作为这个 profile 的别名。

## 本机结果

- Arduino IDE 2 内置 CLI 0.32.3 可用，但只安装 `arduino:avr 1.8.6`。
- Mind+ 2 内置 CLI 0.33.1 可用，安装了 `mindplus:esp32 0.0.1`，但只有 FireBeetle、mPython、Tello 和 FireBeetle Mesh 等专属板型。
- PlatformIO Core 6.1.11 存在，但 Development Platforms、Tools、Toolchains 和 Global Libraries 均为 0。
- 本机没有 ESP-IDF 环境。

因此当前没有精确 DOIT DevKit V1 编译后端。FireBeetle 和 mPython 不会被拿来冒充。

## 已实现的安全进展

- 新增 `chatmaker-esp32` 严格发现层。
- 核对 core inventory 和 `board details`，只有官方 `3.3.11` 与精确 FQBN 同时成立才允许编译。
- 单独记录载板身份；未确认载板时，即使只有一个有线串口也不允许选择上传端口。
- 蓝牙端口被拒绝，CP210x/CH340/CH9102/FTDI 只作为 USB-UART 线索。
- 编译路径只接受 ESP32 `.bin` 产物，不复用 AVR `.hex` 或 Bootloader 策略。
- 环境准备当前只检查和报告，`installation_performed` 始终为 `false`。

## 官方来源

- Arduino-ESP32 3.3.11 `DOIT ESP32 DEVKIT V1` board definition: https://github.com/espressif/arduino-esp32/blob/3.3.11/boards.txt#L19873-L19901
- DOIT variant pins: https://github.com/espressif/arduino-esp32/blob/3.3.11/variants/doitESP32devkitV1/pins_arduino.h
- Arduino-ESP32 installation guide: https://github.com/espressif/arduino-esp32/blob/3.3.11/docs/en/installing.rst
- Espressif ESP32 GPIO restrictions: https://github.com/espressif/esp-idf/blob/v5.5.5/docs/en/api-reference/peripherals/gpio/esp32.inc

## 仍未验证

- 官方 core 尚未安装，因此 Blink 与 AP 项目没有真实编译证据。
- 没有有线 DOIT ESP32 DevKit V1，因此烧录、串口、Wi-Fi AP、HTTP、LED、传感数据和断电重启均未验证。
- 安装官方 core 会下载较大的第三方工具链，必须获得用户明确授权后才能执行。
