# ChatMaker v0.1.0-rc5

> 状态 / Status: [GitHub 公开预发布版](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc5)。Public GitHub prerelease.

## rc5 之后的当前源码 / Current source after rc5

这次源码更新没有创建新的 GitHub Release，也没有改写 rc1–rc5 的历史证据。它新增确定性的最小 `ChatMaker-Core-<version>.zip`：只包含运行层、四个 Skill 目录、schema、4/20/23 规范记录、四个紧凑索引、当前案例、最小文档、Python 元数据和许可证；不包含详细 Knowledge 正文、知识工作区、测试、缓存或可选 `.cmpack` 成品。ChatMaker 是唯一用户入口，ChatDuino、ChatWeb、ChatCAD 只作为内部专业模块。

Nano、Uno、DOIT ESP32 DevKit V1 和星核板各有一个只读 ChatMaker Knowledge 知识包。首次读取缺少的详细章节时，reader 默认从签名注册表自动验证、下载并激活；第二次复用。已安装版本可离线重校验后读取；缓存只有在签名 receipt 未过期时才能授权新的离线安装。更新和回滚只由 `chatmaker-pack` 处理，不会修改 Codex/WorkBuddy 配置。自动安装范围不包括驱动、Mind+、Arduino Core、Node、Chromium、PATH、安装钩子或管理员操作。

WorkBuddy 当前源码服务版本为 `1.14.0`，共有 33 个工具，使用共用的 `knowledge_get`，并包含 `cad_component_profile_get` 和另外三个 ChatCAD 工具。这条说明描述 rc5 之后的源码，不改变下面 rc5 发布物当时的 `1.7.0` / 23 工具事实。

星核板 v4.2.2 Knowledge 1.4.0 现已按完整开发资料重做板级审计：补齐 42 个 GPIO/别名/电源/CAN 信号记录，板载 A/B 按键、无源蜂鸣器、QMI8658、CH9102F、SIT3051TK、四类电源入口和 3.3V/5V I2C 接口；并明确掌控板兼容目标中的 `display/rgb/light/sound` 不是星核板板载实物，QMI8658 的当前公开对象只验证加速度与手势，不把芯片内陀螺仪误写成可直接调用。板载按键/蜂鸣器与 CAN 监听代表程序已在 Mind+ 1.8 编译通过，上传、总线通信和物理效果仍未验证。ChatMaker 在 WorkBuddy 缺少内部 Skill 或 `knowledge_get` 时会报告安装不完整，不再把未执行的知识查询描述成“已经查过”。安装器同时识别新版 WorkBuddy 的 `.mcp.json` 和旧版 `mcp.json`。

This source update creates no new GitHub Release and does not rewrite rc1–rc5 evidence. It adds a deterministic minimal `ChatMaker-Core-<version>.zip` containing runtime code, four Skill directories, schemas, canonical 4/20/23 records, four compact indexes, current examples, minimal documentation, Python metadata, and the license. Detailed Knowledge bodies, the knowledge workspace, tests, caches, and optional built `.cmpack` artifacts are excluded. ChatMaker is the only user entry; ChatDuino, ChatWeb, and ChatCAD are internal specialists.

Nano, Uno, DOIT ESP32 DevKit V1, and Starcore each have one read-only ChatMaker Knowledge pack. A first detailed-section read verifies, downloads, and activates an absent pack from the signed registry; later reads reuse it. Installed content remains readable after offline revalidation, while cached content can authorize a new offline install only before its signed receipt expires. Only `chatmaker-pack` performs content update and rollback, without editing Codex/WorkBuddy configuration. Automatic content installation never includes drivers, Mind+, Arduino cores, Node, Chromium, PATH changes, hooks, or administrator actions.

Current source uses WorkBuddy server `1.14.0` with 33 tools, including shared `knowledge_get`, `cad_component_profile_get`, and the other three ChatCAD tools. The rc5 section below remains an accurate historical description of the rc5 artifact's `1.7.0` / 23 tools.

Starcore v4.2.2 Knowledge 1.4.0 now reflects a full board-level audit of the owned development sources. It records 42 GPIO, alias, power, and CAN signals; onboard A/B buttons, passive buzzer, QMI8658, CH9102F, SIT3051TK, four power-input paths, and both 3.3 V and level-shifted 5 V I2C banks. It also states that the mPython-compatible `display/rgb/light/sound` objects do not prove onboard Starcore hardware, and that the reviewed QMI8658 public object exposes acceleration and gestures rather than gyroscope readings. Representative onboard-button/buzzer and CAN-listen sketches compile with Mind+ 1.8; upload, bus traffic, and physical effects remain unverified. ChatMaker reports an incomplete WorkBuddy installation when internal Skills or `knowledge_get` are unavailable instead of claiming that an unperformed Knowledge search succeeded. The installer recognizes both current WorkBuddy `.mcp.json` and legacy `mcp.json` configurations.

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
