# ChatMaker v0.1.0-rc5

> 状态 / Status: [GitHub 公开预发布版](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc5)。Public GitHub prerelease.

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
