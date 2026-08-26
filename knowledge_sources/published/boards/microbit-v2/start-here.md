---
schema_version: "1.0"
kind: knowledge-page
stable_id: microbit-v2-start-here
board_id: microbit-v2
section_id: start-here
source_refs: [source-microbit-v2-official]
---
# 从 micro:bit V2 身份开始

先确认板卡是 BBC micro:bit V2.x，再读取板卡记录 `microbit-v2`。V2 使用 nRF52833，不能把 V1 的核心、内存或程序包当作 V2 使用。官方参考尺寸为 51.6×42.0 mm；紧配外壳仍需拿实板复核。

当前推荐起点是 MicroPython V2：检查 Python 源码、生成 HEX 文件，再由板载 DAPLink 接口写入。没有实板时已经验证到环境、源码、HEX 和虚拟目标盘；真实写入、串口、断电重启、LED 与按键仍需实板。
