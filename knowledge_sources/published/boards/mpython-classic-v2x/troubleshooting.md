---
schema_version: "1.0"
kind: knowledge-page
stable_id: mpython-classic-v2x-troubleshooting
board_id: mpython-classic-v2x
section_id: troubleshooting
source_refs: [source-mpython-classic-v2x-official]
---
# 从板型开始排错

先确认经典版而不是 3.0 或星核板，再确认 V2.x 修订版本。然后依次检查 USB 数据线、唯一有线端口、Mind+ 版本对应的编译目标、缺失扩展、编译、上传、重启和串口输出。

加速度或指南针异常时，不要先改算法：先核对 MSA300/QMI8658C 与 MMC5983MA/MMC5603NJ 的版本组合。自动探测仍无法确认时，告诉用户在板子背面查找版本字样；用户看不懂就请其拍摄正反面照片。
