# Arduino Uno Rev3 Mind+ 编译验收

## 独立板卡参数

2026-08-15 从本机 Mind+ 原始板卡定义核对：

```text
Mind+ 1.x FQBN: arduino:avr:uno
Mind+ 2.x FQBN: mindplus:avr:uno
MCU: ATmega328P
上传协议: arduino
上传速度: 115200
```

Uno 适配器不使用 Nano 的 `mindplus:avr:nano:cpu=atmega328`，也不使用 Nano 的 57600 后回退 115200 策略。

## 真实编译

```text
示例: examples/chatduino/uno/blink/blink.ino
后端: mindplus-2-cli
FQBN: mindplus:avr:uno
结果: success true
HEX: blink.ino.hex
程序空间: 2008 / 32256 bytes
动态内存: 204 / 2048 bytes
```

编译产物生成于独立的 `uno-mindplus-builds` 临时目录，不与 Nano 构建目录共用。

## 自动测试边界

- Mind+ 1.x 与 2.x 编译命令均检查为 Uno FQBN。
- Uno 上传命令固定为 115200，并且一次同步失败后不尝试 Nano 的 57600/115200 回退。
- 蓝牙端口会被拒绝；多个有线端口会停止并要求选择。
- 没有有线 Uno 时，编译成功后进入 `awaiting-hardware`，不报告烧录成功。

## 未验证

- 当前没有接入有线 Arduino Uno，因此没有执行固件烧录。
- 串口 `UNO_BLINK_READY`、断电重启和板载 LED 闪烁均未验证。
- 本次 Uno 结果不能用于证明 Nano 或 ESP32 的编译、烧录或物理效果。
