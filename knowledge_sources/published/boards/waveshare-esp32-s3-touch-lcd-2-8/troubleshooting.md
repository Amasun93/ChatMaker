---
schema_version: "1.0"
kind: knowledge-page
stable_id: waveshare-esp32-s3-touch-lcd-2-8-troubleshooting
board_id: waveshare-esp32-s3-touch-lcd-2-8
section_id: troubleshooting
source_refs: [source-waveshare-esp32-s3-touch-lcd-2-8-official]
---
# 看看卡在哪一步

- 找不到板型时，先核对加载的是当前 ChatMaker，搜索完整型号加 V2。用板背的字确认型号，2.8B 和 2.8C 各走自己的路线。
- 下载进度出现时，看工具报告里的组件名称和剩余字节。第一次缺编译器或 V2 驱动归档时，由 ChatMaker 准备。已有缓存的环境应尽量复用，相同项目改效果通常只需重新编译。
- 电脑找不到板子时，先检查 USB 线是否可以传数据。看到端口后，若有多块板再确认要写哪块。
- 画面能亮但点按无反应时，核对是否使用了实物对应的版本，再用计时器验证开始、暂停和重置。
- Windows 报 `bits/error_constants.h` 或 `bits/c++config.h` 找不到时，查看是否走了本机托管 ESP32-S3 工具链。ChatMaker 会给 GCC 传入标准库和 ESP32-S3 的目标头文件绝对路径。若较深目录仍失败，在新建的短路径工具目录复测。已有工具缓存可保留做对照。
- 脱离串口助手玩时掉帧，先暂停循环里的 `Serial.print`、`printf` 和触摸事件日志。把帧间隔放在内存，收到诊断命令再汇报。USB 有连接时，电脑仍可能暂时读不动，单次写入的设置也会受到驱动多次重试影响。
- 旧球在画面上留下持续轨迹时，先用同尺寸缓冲区在内存合成背景和球，再一次覆盖整个游戏区。Issue #6 的 v6.4 在真板验证这条路线有效。局部擦除失效机制仍待定位。仅凭外观也无法判断持续残影是否属于屏幕撕裂。[Issue #6 实测](https://github.com/Amasun93/ChatMaker/issues/6)

本仓库记录了 V1/V2 真实编译。2026-11-18 在 Windows 的同一项目目录复测 V2，准备预览显示待下载 0 字节，第二次准备直接复用了工具，触屏计时器生成了固件。实板写入、触摸和断电重启继续以实际观察记录为准。[微雪官方 FAQ](https://docs.waveshare.net/ESP32-S3-Touch-LCD-2.8/FAQ/)
