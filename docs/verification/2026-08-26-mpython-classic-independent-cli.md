# 经典掌控板 V2.x 独立 CLI 最小闭环验证

日期：2026-08-26

平台：Windows x64

板卡目标：经典掌控板 V2.0–V2.3 家族（`mpython-classic-v2x`）

代表案例：`examples/chatduino/mpython-classic-v2x/chinese-status/chinese-status.ino`

## 范围卡

- 必须改：补齐不依赖 Mind+ 桌面应用的环境、doctor、编译、端口、安全上传、复位和串口读取入口，并真实编译一个中文静态屏案例。
- 绝不改：不套用掌控板 3.0 或星核板实体身份，不恢复 MCP，不修改 ChatCAD/ChatPPT/SkillHub/CDN，不把命令结果升级成未观察的实体效果。
- 验收证据：环境、源码、编译、上传、串口、断电重启和实体效果七门分开；没有经典掌控板实物确认时停在编译门。

## 官方来源和锁定工具链

- Arduino CLI `0.33.1` Windows 64-bit ZIP：14,311,609 字节，SHA-256 `58e7474a5873dbd7cad811ed4193223497d90445a6312397a65c08156b6c96d3`，官方发行压缩包携带 GPL-3.0。
- Mind+ 官方包索引：`https://resource.mindplus.top/mindplus/package/package_mindplus_index.json`。
- `mindplus:esp32@0.0.1`：35,008,313 字节，SHA-256 `00b08da1ee9e42a08480868ec2f8ec5c5159f7f54c6dec3fe4ba05eaa41ef0db`，核心压缩包携带 LGPL-2.1。
- FQBN：`mindplus:esp32:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none`。
- 六个官方 `1.0.0` 库：`DFRobot_Mindplus_MPython`、`DFRobot_Mindplus_NeoPixel`、`DFRobot_Mindplus_SSD1306`、`DFRobot_MPython_Font`、`DFRobot_Mindplus_ASCIIfont`、`DFRobot_Mindplus_CHfont`。各自的来源、大小和 SHA-256 由 `chatmaker-mpython doctor` 返回。

六个库的官方压缩包没有携带统一许可证文件。本实现只保存 URL、大小和 SHA-256，并从 DFRobot/Mind+ 官方地址在用户本机下载；在许可证进一步确认前，不把这些库重新打包进 ChatMaker 发行物。

## 真实结果

`prepare-environment` 命中现有 ChatMaker 隔离目录并通过完整性检查，`installation_performed=false`、`ready_for_compile=true`。它没有安装、启动或引用 Mind+ 桌面应用。

当前复用了先前星核板阶段已下载的同一套 mPython 编译资产，因此磁盘目录仍保留历史名称 `toolchains/starcore`；运行层对外报告的是中性资产档案 `mindplus-esp32-0.0.1`。这只是避免重复下载约 50 MB 工具文件，不共享或推断任何星核板实体身份、板载硬件或实物证据。

代表案例使用 `chatmaker-managed-mpython-classic` 编译成功，退出码 0：

- 源码 SHA-256：`65ab0cc4c926d0d6b9ad76143e352bf4eb0b9f59756a3e1ba4bfe9174b2988d1`
- Flash：272,100 字节（20%）
- 动态内存：17,812 字节（6%）
- 应用 BIN：272,208 字节，SHA-256 `2ea78431816caad1a327eb6c2a86df33f5477de8d44842924e9ec6d9e69978f8`
- 分区 BIN：3,072 字节，SHA-256 `efba4421982bd177695a2e2091828fe3b6aa42076be3844a84f0fb08085cead4`

案例只在 `setup()` 中绘制“掌控板就绪 / ChatMaker”，`loop()` 不清屏、不重绘整屏，只输出每秒串口心跳，避免明显闪烁。

## 证据门

| 证据门 | 状态 | 说明 |
| --- | --- | --- |
| 环境 | 已验证 | 隔离工具链存在且完整性检查通过 |
| 源码 | 已验证 | 中文静态状态页已签入并记录 SHA-256 |
| 编译 | 已验证 | 独立链退出码 0，应用和分区产物存在 |
| 上传 | 未验证 | 当前没有确认连接的是经典掌控板 V2.x；未向 COM4 写入 |
| 串口 | 未验证 | 未在经典掌控板上读取 READY/HEARTBEAT |
| 断电重启 | 未验证 | 没有可用经典掌控板实物 |
| 实体效果 | 未验证 | 未肉眼确认 OLED 中文、方向、清晰度或闪烁情况 |

`chatmaker-mpython` 的上传和复位动作都要求明确的经典掌控板身份确认；蓝牙端口被拒绝，多条有线端口不会自动选择。上传成功也只说明写入命令成功，复位动作只说明控制线已切换，二者都不会自动证明板卡启动、串口输出或 OLED 显示。

复位控制线依据 Espressif esptool 官方自动复位说明与 v2.6 `hard_reset()` 行为：DTR 保持非下载模式，RTS 将 EN 拉低约 100 ms 后释放。来源：<https://docs.espressif.com/projects/esptool/en/latest/esp32/advanced-topics/boot-mode-selection.html>、<https://github.com/espressif/esptool/blob/v2.6/esptool.py>。
