---
schema_version: "1.0"
kind: knowledge-page
stable_id: mpython-v3-troubleshooting
board_id: mpython-v3
section_id: troubleshooting
source_refs: [source-mpython-v3-official]
---
# 先排除经典版工具链

看到 ESP32-S3 或彩屏后，先确认加载的是 `mpython-v3`，而不是经典 `dfrobot:mpython:mpython` 目标。然后检查本机是否真的安装 3.0 平台包、板卡定义、库和示例；下载索引中有记录不等于工具链已经可用。

官方 3.0 文档仍在迭代，个别页面有产品代数笔误或残留合并标记。遇到冲突时保留来源并降低证据等级。自动识别仍不确定时，引导用户查看板名丝印；看不懂就请其拍正反面照片。
