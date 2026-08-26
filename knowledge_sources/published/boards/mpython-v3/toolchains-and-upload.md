---
schema_version: "1.0"
kind: knowledge-page
stable_id: mpython-v3-toolchains-and-upload
board_id: mpython-v3
section_id: toolchains-and-upload
source_refs: [source-mpython-v3-official]
---
# 使用掌控板 3.0 独立工具链

Windows x64 可使用 `chatmaker-mpython-v3` 的 `prepare-environment`、`doctor`、`ports`、`compile` 和 `compile-upload` 动作。ChatMaker 从 Labplus 官方索引安装固定的 `mpython:esp32@3.0.0`、ESP32-S3 编译器和烧录工具，不要求预先安装 Mind+ 桌面应用。电脑里已有 Mind+ 仍可保留，但不是独立链的前置条件。

编译目标只能是 `mpython:esp32:labplus_mpython_v3`。上传前必须确认实板确实是掌控板 3.0，并且只剩一个合格有线端口；不能回退到经典掌控板或星核板目标。编译、上传、串口、断电重启和彩屏显示分别报告。
