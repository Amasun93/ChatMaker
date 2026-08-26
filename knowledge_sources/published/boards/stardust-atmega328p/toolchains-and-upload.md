---
schema_version: "1.0"
kind: knowledge-page
stable_id: stardust-atmega328p-toolchains-and-upload
board_id: stardust-atmega328p
section_id: toolchains-and-upload
source_refs: [source-stardust-atmega328p-observed]
---
# 使用已验证的兼容链

当前实板以 `mindplus:avr:nano:cpu=atmega328` 完成编译，并在 115200 上传成功；57600 会出现引导程序同步失败。这个目标只表示兼容编译和上传，不改变星辰板的独立产品身份。

上传前必须确认星辰板身份和唯一有线端口。上传退出码、串口标记、物理断电重启和实体显示是四个不同结果。
