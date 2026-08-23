# ChatMaker v0.1.0-rc5

> 状态 / Status: [GitHub 公开预发布版](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc5)。Public GitHub prerelease.

## rc5 之后的当前源码 / Current source after rc5

这次源码更新没有创建新的 GitHub Release，也没有改写 rc1–rc5 的历史证据。当前 Core 源码包含运行层、四个 Skill 目录、schema、七块板卡记录、六个紧凑索引、当前案例、最小文档、Python 元数据和许可证；详细 Knowledge 正文继续以只读知识包提供。ChatMaker 是唯一用户入口，ChatDuino、ChatWeb、ChatCAD 只作为内部专业模块。

Nano、Uno、DOIT ESP32 DevKit V1、星核板、经典掌控板 V2.x 和掌控板 3.0 各有一个只读 ChatMaker Knowledge 知识包。两代掌控板按芯片、屏幕、引脚、传感器和 API 分开维护。首次读取缺少的详细章节时，reader 默认从签名注册表自动验证、下载并激活；第二次复用。

WorkBuddy 当前源码服务版本为 `1.17.0`，共有 36 个工具。新增 `board_identify`：先做无损读取；允许时在完整备份后刷入临时识别程序并恢复；仍不确定时引导用户查看型号或拍正反面照片。这条说明不改变下面 rc5 发布物当时的 `1.7.0` / 23 工具事实。

星核板 v4.2.2 Knowledge 1.5.0 在 1.4.0 完整板级审计上补入实板证据：一块用户确认的 v4.2.2 已完成 Mind+ 1.8 编译、上传、115200 串口、QMI8658 静止数据、16 MiB 全量备份和逐字节恢复验证；新增 `onboard-self-test` 示例。完整备份读取从 115200 提升到经实板验证的 460800，完整识别事务从约 28 分钟降至约 11 分钟，恢复仍保持 115200。电子探针仍不能只凭 ESP32、CH9102F 或 QMI8658 区分星核板与经典掌控板，因此继续要求固件精确标记、丝印或照片。按键按下、实际可听蜂鸣、CAN、断电重启和七个外接模块仍未验证。

This source update creates no new GitHub Release and does not rewrite rc1–rc5 evidence. The current Core source contains runtime code, four Skill directories, schemas, seven board records, six compact indexes, current examples, minimal documentation, Python metadata, and the license. Detailed Knowledge bodies remain read-only optional packs. ChatMaker is the only user entry; ChatDuino, ChatWeb, and ChatCAD are internal specialists.

Nano, Uno, DOIT ESP32 DevKit V1, Starcore, classic mPython V2.x, and mPython 3.0 each have one read-only ChatMaker Knowledge pack. The two mPython generations keep separate chip, display, pin, sensor, and API facts.

Current source uses WorkBuddy server `1.17.0` with 36 tools. The new `board_identify` tool performs safe reads first, may use a backed-up and restored temporary probe, and falls back to markings or front/back photos. The rc5 section below remains an accurate historical description of the rc5 artifact's `1.7.0` / 23 tools.

Starcore v4.2.2 Knowledge 1.5.0 adds physical-board evidence to the 1.4.0 board audit. One user-confirmed v4.2.2 completed Mind+ 1.8 compilation, upload, 115200 serial output, static QMI8658 readings, a full 16 MiB backup, and byte-verified restoration; an `onboard-self-test` example is included. Full-backup reads now use a hardware-verified 460800 baud, reducing the full identification transaction from about 28 to about 11 minutes while restore remains at 115200. ESP32, CH9102F, or QMI8658 still cannot electronically distinguish Starcore from classic mPython on their own, so an exact firmware marker, markings, or photos remain required. Pressed-button behavior, audible buzzer output, CAN, power-cycle recovery, and the seven external modules remain unverified.

## 中文

rc5 把 rc4 之后已经完成的软件能力整理为一个可安装、可复核的候选包。Nano 和 Uno 继续使用 Mind+ 1.x/2.x；ESP32 只使用官方 Arduino CLI、锁定的 `esp32:esp32@3.3.11` Core 和精确 FQBN `esp32:esp32:esp32doit-devkit-v1`。

### 相对 rc4 的新增内容

- 新增受控的 ESP32 官方环境准备、doctor、端口、编译和安全编译—上传入口；Blink 与 AP 固件可独立编译。
- 新增 ESP32 SoftAP 手机控制案例。`examples/chatweb/esp32-ap-control.html` 是唯一可编辑页面源，`chatmaker-web-embed` 生成固件内嵌的 `page_html.h`。
- 新增可执行 `chatmaker-route`，把项目路由到硬件、网页、软硬件组合或澄清阶段；组合项目必须先明确通信协议。
- 新增 `chatmaker-web-plan` 创意简报规划。小白默认只得到两到三条精选方向；额外方向和 `chatmaker-web-playground` 只有显式 `--advanced` 时出现。
- 新增真实 Chromium 自动化，覆盖课堂页、模拟硬件页、ESP32 AP 页和高级游乐场的主要交互、手机宽度、触控尺寸与控制台错误。
- WorkBuddy stdio 服务版本为 `1.7.0`，列出 23 个工具：2 个资料工具、Nano/Uno/ESP32 各 5 个工具、6 个串口工具。
- 发布包包含 Python 安装元数据、Codex/WorkBuddy 安装器、Node/Playwright 浏览器测试依赖和所有 rc5 源码。

### 证据边界

本候选的自动测试、浏览器测试和编译结果只证明对应的软件门。没有有线 Nano、Uno 或已确认身份的 DOIT ESP32 DevKit V1 时，不会执行上传。Nano/Uno/ESP32 的真实烧录、启动串口、断电重启和物理效果，以及 ESP32 的 SoftAP、手机连接和真实 HTTP 往返，都必须单独验证。

rc1、rc2、rc3 和 rc4 继续作为历史发布保留；本文件描述 rc5，不改写它们当时的验证记录。

## English

rc5 packages the software capabilities developed after rc4 into an installable and reviewable candidate. Nano and Uno still use Mind+ 1.x/2.x. ESP32 uses only an official Arduino CLI, the locked `esp32:esp32@3.3.11` core, and the exact `esp32:esp32:esp32doit-devkit-v1` FQBN.

### New since rc4

- Controlled official ESP32 environment preparation, doctor, port, compile, and guarded compile-upload commands; the Blink and AP firmware compile independently.
- An ESP32 SoftAP phone-control example. `examples/chatweb/esp32-ap-control.html` is the only editable page source, and `chatmaker-web-embed` generates the embedded `page_html.h`.
- Executable `chatmaker-route` routing to hardware, web, combined, or clarify; combined projects stay blocked until a communication contract exists.
- Executable `chatmaker-web-plan` creative planning. Beginners receive only two or three curated directions; expanded directions and `chatmaker-web-playground` require explicit `--advanced` opt-in.
- Real Chromium automation for the classroom, simulated-hardware, ESP32 AP, and advanced-playground pages, including primary interactions, phone layout, touch size, and console-error checks.
- WorkBuddy stdio server `1.7.0` with 23 tools: 2 catalog tools, 5 each for Nano, Uno, and ESP32, plus 6 serial tools.
- Python installation metadata, Codex/WorkBuddy installers, Node/Playwright browser-test dependencies, and all rc5 sources in the archive.

### Evidence boundary

Automated tests, browser checks, and compilation prove only their respective software gates. Without a wired Nano, Uno, or identity-confirmed DOIT ESP32 DevKit V1, no upload is attempted. Real upload, boot serial, power-cycle, and physical effects for every board—and ESP32 SoftAP, phone connection, and real HTTP round trips—remain separate hardware gates.

rc1, rc2, rc3, and rc4 remain historical releases. This file describes rc5 and does not rewrite their contemporary verification records.
