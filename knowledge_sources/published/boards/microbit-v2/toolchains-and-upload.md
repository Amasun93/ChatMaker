---
schema_version: "1.0"
kind: knowledge-page
stable_id: microbit-v2-toolchains-and-upload
board_id: microbit-v2
section_id: toolchains-and-upload
source_refs: [source-microbit-v2-official]
---
# 独立准备程序和安全下载

当前固定使用 MicroPython V2 2.1.1 与 `microbit-fs` 0.10.0，把 `main.py` 合成可写入的 HEX。这一步叫“HEX 打包”，不是 CODAL/C++ 原生编译。固定版本和校验值记录在板卡资料与验证文档中。

写入前先验证唯一的 `MICROBIT` 目标盘；有多个目标时必须明确选择。写入完成后继续分别检查 `FAIL.TXT`、设备重新连接、115200 串口、断电重启和实体效果。当前前半段已通过软件验证，后半段等待实板。
