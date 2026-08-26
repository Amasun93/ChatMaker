---
schema_version: "1.0"
kind: knowledge-page
stable_id: microbit-v2-identify-and-safety
board_id: microbit-v2
section_id: identify-and-safety
source_refs: [source-microbit-v2-official]
---
# 识别板卡和目标盘

板卡必须先确认是 V2.x。电脑端只把卷标为 `MICROBIT`、包含 `DETAILS.TXT` 且接口版本符合 V2 范围的盘识别为普通程序目标；普通 U 盘、缺少身份文件的盘和 V1 接口均应拒绝。

`MAINTENANCE` 是接口芯片维护盘，不是普通程序盘，不要把项目 HEX 写进去。文件复制完成也不等于程序已启动，更不等于 LED 或按键效果正常。
