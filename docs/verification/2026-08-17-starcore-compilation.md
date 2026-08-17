# 星核板基础编译验证

- 日期：2026-08-17
- 板卡：IDMC-0001 星核板 v4.2.2
- 当前目标：`dfrobot:mpython:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none`
- 工具链：本机已有 Mind+ 1.x `E:\Mind+`
- 示例：`examples/chatduino/starcore/blink/blink.ino`
- 结果：真实编译通过，程序 205716 / 1310720 bytes，动态内存 15260 / 294912 bytes。
- 未验证：实体板识别、烧录、重启、串口标记、P13 外接 LED 和其他物理效果。

Mind+ 2.0 的 `mindplus:esp32:mpython:...` 只保留为历史目标，本次没有用它代替当前目标。
