---
schema_version: "1.0"
kind: knowledge-page
stable_id: mpython-classic-v2x-libraries-and-examples
board_id: mpython-classic-v2x
section_id: libraries-and-examples
source_refs: [source-mpython-classic-v2x-official]
---
# Arduino 与 MicroPython API 分开看

Arduino 的 `MPython.h` 提供 `mPython.begin()`、`display`、`rgb`、`buzz`、按键、触摸、声光输入和 `accelerometer`。本机库会探测 MSA300 或 QMI8658，但公开 Arduino 全局对象没有等价的陀螺仪对象。

MicroPython 使用 `from mpython import *`，经典显示对象是 `oled`，并有 `light.read()`、`sound.read()`、`accelerometer`、`gyroscope` 和 `magnetic` 等官方文档。API 页对 V2.3 的描述存在版本条件，生成程序前应同时检查板背版本和所用固件。

