---
schema_version: "1.0"
kind: knowledge-page
stable_id: idmc-0001-starcore-v4-2-2-web-and-protocol
board_id: idmc-0001-starcore-v4-2-2
section_id: web-and-protocol
source_refs:
  - source-idmc-0001-starcore-v4-2-2-owned-docs
---
# 网页和星核板协作

网页项目先定义通信合同，再分别开发 ChatWeb 和 ChatDuino：使用串口、局域网 HTTP、WebSocket 或其他传输；页面会发送什么；板卡会返回什么；断线、超时和错误怎样显示。不要先写漂亮页面，再临时猜测固件接口。

每条消息使用稳定字段和明确单位。例如传感器数据同时给出名称、数值、单位和时间；控制命令包含动作与目标状态。板卡负责硬件安全默认值，网页负责清楚显示连接状态，双方都不能把“按钮点击成功”当成执行器已经动作。

网页预览只证明浏览器交互。固件编译只证明代码通过编译。网络连接、协议往返和物理效果需要分别观察并记录；缺少实板时保留为 `unverified`。
