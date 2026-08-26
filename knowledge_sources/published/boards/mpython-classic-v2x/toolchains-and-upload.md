---
schema_version: "1.0"
kind: knowledge-page
stable_id: mpython-classic-v2x-toolchains-and-upload
board_id: mpython-classic-v2x
section_id: toolchains-and-upload
source_refs: [source-mpython-classic-v2x-official]
---
# 首选 ChatMaker 独立链，Mind+ 保留兼容

Windows x64 首选 `chatmaker-mpython`。它复用 ChatMaker 已校验的隔离 mPython Arduino 工具链：Arduino CLI `0.33.1`、`mindplus:esp32@0.0.1` 和六个固定 `1.0.0` 库，不需要安装或启动 Mind+ 桌面应用。每个下载物都固定来源、大小和 SHA-256；doctor 会返回完整锁定清单。

Arduino CLI 发行压缩包携带 GPL-3.0，Mind+ 核心压缩包携带 LGPL-2.1。六个官方库压缩包没有统一许可证文件，因此 ChatMaker 只从 DFRobot/Mind+ 官方地址在运行时下载，不把它们重新打包进发行物。

Mind+ 1.8 使用 `dfrobot:mpython:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none`；本机 Mind+ 2.0 使用 `mindplus:esp32:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none`。它们是两套目标，不能混用路径和上传控制参数。

中文静态状态页已在独立链上完成真实编译。当前未确认连接的是经典掌控板，因此上传、复位后启动、串口、断电重启和 OLED 肉眼效果仍未验证。上传和复位都要求 `board_confirmed=true`，蓝牙端口会被拒绝，多条有线端口必须明确选择。临时识别程序也只有在备份和恢复链路满足保护条件时才能写入。
