# 星核板课堂配方聚焦编译记录（2026-08-21）

本次只验证新增的两个课堂配方，没有重复编译旧示例全集。

目标板型：

```text
dfrobot:mpython:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none
```

调用 ChatMaker 的星核板编译入口，内部使用当前 Mind+ 1.8 `arduino-builder`：

| 配方 | 源文件 | 退出码 | 应用固件 |
| --- | --- | ---: | --- |
| `starcore-ws2812-classroom-strip` | `examples/chatduino/starcore/starcore-ws2812-classroom-strip/starcore-ws2812-classroom-strip.ino` | 0 | 已生成 `.ino.bin` 和 partitions 二进制 |
| `starcore-sg90-safe-position` | `examples/chatduino/starcore/starcore-sg90-safe-position/starcore-sg90-safe-position.ino` | 0 | 已生成 `.ino.bin` 和 partitions 二进制 |

结论：这两个已检入源码能为精确星核板目标生成固件。当前没有实体板，因此烧录、串口输出、灯带显示、舵机运动和断电重启均保持未验证。
