---
schema_version: "1.0"
kind: knowledge-page
stable_id: idmc-0001-starcore-v4-2-2-troubleshooting
board_id: idmc-0001-starcore-v4-2-2
section_id: troubleshooting
source_refs:
  - source-idmc-0001-starcore-v4-2-2-owned-docs
---
# 按证据层级排错

先确认板型和 Mind+ 目标，再看错误发生在哪一层：找不到头文件通常是扩展未添加；找不到有线串口先检查 USB 数据线、驱动和蓝牙端口排除；启动失败检查启动敏感引脚；传感器始终为零先检查供电、S/V/G 线序、信号电平和读取节拍。

OLED 英文正常但中文异常时，优先检查 Mind+ 的中文字库写入状态，不要直接换显示库。DHT11 默认从 P0 和 3.3V 起步；P14 只用于排障对比。超声波返回零时区分超时、接线、模块批次和 ECHO 电平。电机或舵机导致重启时先检查独立电源、共地和堵转电流。

CAD 文件生成成功只证明几何文件已产生。加工前仍要核对孔径、公差、USB-C 开口、定位件和线束空间，并用真实 v4.2.2 板卡试装。最终报告只写已经观察到的最高状态，并列出下一项缺失验证。
