---
schema_version: "1.0"
kind: knowledge-page
stable_id: mpython-v3-pins-and-electrical
board_id: mpython-v3
section_id: pins-and-electrical
source_refs: [source-mpython-v3-official]
---
# 3.0 有自己的引脚表

P0–P4 对应 GPIO1–5，P19 是 GPIO43/SCL，P20 是 GPIO44/SDA；P7/GPIO8 连接板载 RGB，P10/GPIO6 与声音输入相关，P11/GPIO46 是 B 键，P12/GPIO21 与发声相关。完整映射以 `mpython-v3` 板卡记录为准。

不要从经典掌控板复制 GPIO22/23 的 I2C 映射。外接 I2C 设备前先检查板载器件和地址占用，所有外部输入保持 3.3V 逻辑。

