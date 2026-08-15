<p align="right">
  <a href="README_EN.md">English</a> · <b>简体中文</b>
</p>

<h1 align="center">ChatMaker</h1>

<p align="center">
  <b>让不懂专业开发的人，也能和 AI 一起做出有趣、好看、可以运行的作品。</b>
</p>

ChatMaker 是面向老师、学生和黑客松参与者的 AI 创作伙伴。用户说出想法、选择喜欢的方向并确认实际效果。ChatMaker 负责启发创意、设计方案、生成代码、调用工具和检查结果。

对话窗口就是创作环境。Mind+、编译器、串口和浏览器在后台完成专业工作，用户不需要先学习一套 IDE。

> 当前处于早期开发阶段。[`v0.1.0-rc5`](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc5) 已作为 GitHub 预发布版公开。它包含 Nano/Uno Mind+ 编译、ESP32 官方 Core 准备与精确 FQBN 编译、手机 AP 页面嵌入、可执行路由和创意规划、显式高级游乐场、WorkBuddy 1.7.0 的 23 个工具，以及真实 Chromium 自动化。没有匹配实板证据，因此仍不能声称完成烧录或实物闭环。

## 它补上的能力

普通代码生成器通常从一条技术指令开始。小白用户更常见的起点是“我想让课堂有趣一点”“我有一块板子，不知道能做什么”。

ChatMaker 补上四件事。

| 能力 | ChatMaker 怎样处理 |
| --- | --- |
| 创意引导 | 想法模糊时每轮只问一两个问题，再提供两到三套经过筛选的方案 |
| 专业实现 | 把用户选择变成接线、程序、页面、编译、烧录和浏览器操作 |
| 渐进复杂度 | 小白默认看到最少选项，需要更多时才展开样式库和高级游乐场 |
| 真实验证 | 分开报告资料核对、代码编译、固件烧录、串口或浏览器结果和实物效果 |

## 三个创作伙伴

```text
ChatMaker
├─ ChatDuino   硬件、接线、固件、编译、烧录、串口
└─ ChatWeb     前端创作、课堂工具、设备界面、浏览器验证
```

### ChatMaker

理解用户想完成的作品，帮助整理目标并选择路线。需要软硬件协作时，它会先约定页面发送什么、设备返回什么，再让两个模块分别实现。

### ChatDuino

帮助用户识别板卡和模块，给出简单直白的文字接线、完整程序和真实编译结果。第一阶段复用 Mind+ 工具链，下一阶段再开发不依赖 Mind+ 的托管环境。

默认接线长这样。

```text
【先断电】

1. 光敏模块 VCC → Nano 5V
2. 光敏模块 GND → Nano GND
3. 光敏模块 AO → Nano A0
4. Nano D6 → 330Ω 电阻 → LED 长脚
5. LED 短脚 → Nano GND

接好以后先检查 VCC 和 GND，再插 USB。
```

SVG 和其他图形接线不会默认生成。用户明确需要图片时才作为额外交付物，文字接线始终保留。

### ChatWeb

帮助用户选择视觉与交互方向，制作课堂工具、创意页面和硬件控制界面。小白项目默认生成一个可直接打开的 HTML 文件；复杂项目才拆分文件。更多样式和高级游乐场按需出现。

## 可以怎样使用

从一个清楚的需求开始。

```text
我有一块经典 Nano、光敏模块和 LED，想让天黑后自动亮灯。
```

也可以只有一个模糊方向。

```text
我想做一个能让课堂更有参与感的小工具，但还没有想好形式。
```

或者让网页和硬件一起工作。

```text
帮我设计一个适合手机操作的灯光控制页面，先给我三种视觉方向，
页面确认以后再和 ESP32 的控制程序连接。
```

## 设计哲学

> ChatMaker = 创作伙伴哲学 + 专业事实 + 可执行工具 + 验证证据

ChatMaker 先理解用户要创造什么，再选择合适的模块和工具。每一步结果都是下一步判断的证据。遇到阻碍时，它会根据实际结果调整路线，不在错误方法上反复重试。

Skill 负责告诉 AI 应该怎样判断、哪些技术事实不能猜、什么状态才算完成。容易出错和需要重复执行的动作交给脚本与运行工具。板卡、元器件、程序库、案例和视觉方案放在按需加载的知识包里。

这套结构让 AI 保留判断能力，同时在接线安全、端口选择、编译烧录和完成状态上受到明确约束。

完整设计见 [ChatMaker 创作伙伴设计](docs/plans/2026-08-14-chatmaker-creative-partner-design.md)。

## 当前开发状态

| 范围 | 状态 | 已有证据 |
| --- | --- | --- |
| ChatMaker、ChatDuino、ChatWeb 结构 | 已验证 | 项目校验和 Skill 格式校验通过 |
| 创作伙伴对话规则 | 已写入 | 尚需独立前向测试 |
| 数据包和证据状态 | 已验证 | 自动测试与项目 doctor 通过 |
| Nano Mind+ 编译和烧录迁移 | 部分验证 | 原 33 项行为测试已迁移；10 个示例从 ChatMaker 路径真实编译；烧录等待有线 Nano |
| Uno Mind+ 独立适配器 | 部分验证 | 独立 1.x/2.x FQBN、固定 115200 上传规则、Codex/WorkBuddy 入口和 Blink 真实编译已验证；烧录等待有线 Uno |
| DOIT ESP32 DevKit V1 | 部分验证 | 官方 `esp32:esp32@3.3.11` 已安装；`prepare-environment` 真实 no-op 成功；`esp32:esp32:esp32doit-devkit-v1` 已通过 Blink 和 AP 案例真实编译；烧录、启动、串口、SoftAP、HTTP 和实体效果仍待实板 |
| 常用模块、库和示例 | 首批已验证 | 12 种元器件、14 个配方通过资料校验；10 个 Nano、1 个 Uno 和 2 个 ESP32 示例真实编译 |
| ESP32 AP 手机控制案例 | 部分验证 | `examples/chatweb/esp32-ap-control.html` 是唯一页面源，`chatmaker-web-embed` 生成 `examples/chatduino/esp32/ap-led-sensor/page_html.h`，固件用 `send_P` 和显式长度嵌入页面；浏览器模拟和固件真实编译已通过，硬件仍未验证 |
| ChatWeb 生成和本地预览 | 部分验证 | 3 套方案推荐、单文件生成、课堂页、模拟硬件页和 localhost 预览已通过真实浏览器检查；新增 ESP32 AP 手机页及其接口合同测试，模拟预览不代表硬件已连接 |
| 可执行路由与创意规划 | 已验证 | `chatmaker-route` 返回硬件、网页、组合或澄清路线；`chatmaker-web-plan` 在信息不足时只提问，在信息充分时给出 2–3 条精选方向 |
| 高级方向游乐场 | 显式启用 | 额外方向和 `chatmaker-web-playground` 仅在布尔 `advanced=true` / CLI `--advanced` 时开放 |
| 浏览器自动化 | 已验证 | Chromium 覆盖课堂页、模拟硬件页、ESP32 AP 模拟页和高级游乐场；检查主要交互、390 px 手机布局、至少 44 px 触控目标和零控制台错误 |
| Codex / WorkBuddy 安装 | 开发版已刷新 | 三个 Skill 在 Codex/WorkBuddy 中与仓库哈希一致；WorkBuddy 1.7.0 真实 stdio 服务列出 23 个工具，并保留原有 5 个非 ChatMaker MCP；应用重启后的界面发现仍需单独确认 |
| 串口运行诊断 | 已实现待硬件 | WorkBuddy 6 个串口工具与 Codex JSONL 会话通过自动测试；当前无有线 Nano/Uno，真实日志待现场读取 |
| v0.1.0-rc1 发布候选 | 历史发布 | [GitHub 预发布](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc1)；保留其原始产物与当时验证记录 |
| v0.1.0-rc2 发布候选 | 已发布 | [GitHub 预发布](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc2)；rc1 继续保留，rc2 新增串口运行层 |
| v0.1.0-rc3 发布候选 | 已发布 | [GitHub 预发布](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc3)；包含 12 种模块、11 个配方、10 个编译示例和中文资料目录入口 |
| v0.1.0-rc4 发布候选 | 已发布 | [GitHub 预发布](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc4)；新增独立 Uno 适配器、12 个配方、11 个 AVR 编译示例和 18 个 WorkBuddy 工具 |
| v0.1.0-rc5 发布候选 | 已发布 | [GitHub 预发布](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc5)；193 项 Python 测试、4 项 Chromium 自动化、双 ZIP 确定性构建和下载哈希已验证，实物硬件门仍保持未验证 |
| 不依赖 Mind+ 的环境 | 下一阶段 | 尚未实现 |

## rc5 公开预发布版

当前公开预发布版是 [`v0.1.0-rc5`](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc5)。rc1、rc2、rc3 和 rc4 继续保留各自的历史产物与当时验证记录。

用户可以从 GitHub Release 下载 rc5 ZIP 与同名 `.sha256`，先校验哈希再安装；也可以从公开 `main` 获取当前源码。两种方式都不能把软件测试或编译结果写成真实烧录、串口、网络或物理效果成功。

rc5 新增受控 ESP32 环境准备（只安装官方 `esp32:esp32@3.3.11`）、可执行项目路由、创意简报规划、显式高级游乐场和四页 Chromium 自动化。Nano/Uno 继续使用 Mind+；ESP32 只使用官方 Arduino CLI 和精确 DOIT FQBN。完整安装、命令、前置条件和卸载恢复说明见 [安装说明](docs/installation.md)。

```powershell
Get-FileHash .\ChatMaker-0.1.0-rc5.zip -Algorithm SHA256
Get-Content .\ChatMaker-0.1.0-rc5.zip.sha256
Expand-Archive .\ChatMaker-0.1.0-rc5.zip -DestinationPath .
Set-Location .\ChatMaker-0.1.0-rc5
python -m pip install -e .
python -m unittest discover -s tests -v
python runtime/doctor.py
chatmaker-catalog --request-json '{"action":"search","query":"继电器","kind":"component"}'
chatmaker-route --request-json '{"hardware":{"board":"arduino-nano-classic"}}'
chatmaker-nano --request-json '{"action":"doctor"}'
chatmaker-uno --request-json '{"action":"doctor"}'
chatmaker-esp32 --request-json '{"action":"prepare-environment"}'
chatmaker-nano-examples --root examples/chatduino/nano
chatmaker-web-plan --brief-json '{"kind":"classroom-tool","idea":"收集课堂反馈","audience_scene":"学生下课前使用","desired_feeling":"清楚而轻松","primary_action":"选择最需要重讲的一步"}'
chatmaker-web-embed examples/chatweb/esp32-ap-control.html examples/chatduino/esp32/ap-led-sensor/page_html.h --symbol CHATMAKER_AP_PAGE
chatmaker-web --request-json '{"kind":"classroom-tool","title":"课堂脉冲","prompt":"今天哪一步最需要再讲一次？","primary_label":"我需要再讲一次","direction_id":"editorial-signal"}' --output examples/chatweb/classroom-pulse.html
chatmaker-web-preview examples/chatweb/classroom-pulse.html
npm ci
npx playwright install chromium
npm run test:browser
```

## 项目结构

```text
skills/       三个创作伙伴的判断方式与工作流程
runtime/      编译、烧录、串口、预览等确定性工具
packs/        板卡、模块、案例和视觉方案知识包
examples/     经过验证的完整作品
tests/        自动测试和行为契约
docs/         设计、路线和贡献说明
```

## 路线

1. 继续扩充常用模块、可靠程序库和真实编译示例。
2. 建立 ChatWeb 单文件生成、方案推荐和本地预览。
3. 使用有线 Nano 补做烧录、串口、断电重启和实物效果验收。
4. 增加 Uno、ESP32、串口和软硬件旗舰案例。
5. 开发不依赖 Mind+ 的独立工具链和驱动诊断。
6. 完成 Codex、WorkBuddy 安装器和公开发布包。

详细路线见 [中文说明版](docs/plans/2026-08-14-chatmaker-v0.1-中文说明版.md) 和 [技术实施计划](docs/plans/2026-08-14-chatmaker-v0.1-implementation.md)。

## License

Apache-2.0
