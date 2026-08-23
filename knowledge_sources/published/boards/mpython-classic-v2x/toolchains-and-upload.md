---
schema_version: "1.0"
kind: knowledge-page
stable_id: mpython-classic-v2x-toolchains-and-upload
board_id: mpython-classic-v2x
section_id: toolchains-and-upload
source_refs: [source-mpython-classic-v2x-official]
---
# Mind+ 1.8 与 2.0 要分开

Mind+ 1.8 使用 `dfrobot:mpython:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none`；本机 Mind+ 2.0 使用 `mindplus:esp32:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none`。它们是两套目标，不能混用路径和上传控制参数。

本机已发现两套板卡包和库，但本知识升级没有连接经典掌控板，因此编译、上传、重启、串口和实体效果不能写成已验证。临时识别程序也只有在备份和恢复链路满足保护条件时才能写入。

