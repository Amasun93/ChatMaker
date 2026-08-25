<p align="right">
  <a href="README_EN.md">English</a> · <b>简体中文</b>
</p>

<h1 align="center">ChatMaker</h1>

<p align="center">
  <b>让不懂专业开发的人，也能和 AI 一起做出有趣、好看、可以运行的作品。</b>
</p>

ChatMaker 是面向老师、学生和黑客松参与者的 AI 创作伙伴。用户说出想法、选择喜欢的方向并确认实际效果。ChatMaker 负责启发创意、设计方案、生成代码、调用工具和检查结果。

ChatMaker 是唯一入口；ChatDuino、ChatWeb 和 ChatCAD 是由它在内部调用、分别维护的专业模块。

对话窗口就是创作环境。编译器、串口和浏览器在后台完成专业工作；部分旧板卡仍可复用 Mind+，用户不需要先学习一套 IDE。

> 当前处于 Beta 体验阶段，维护者已邀请 20 多位体验者参与测试。GitHub `main` 是当前推荐安装来源；[`v0.1.0-rc5`](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc5) 只保留为较早的历史快照。各板卡的真实证据按下方状态表分别报告。

## 从 GitHub 安装当前 Beta

把下面这段话和仓库链接交给你正在使用的 AI 即可：

```text
请从这个 GitHub 仓库安装 ChatMaker Skill：
https://github.com/Amasun93/ChatMaker

普通安装只安装 ChatMaker 及其三个内部模块，不扫描 Codex/WorkBuddy，
也不安装额外工具服务。完成后使用 $chatmaker 作为唯一入口。
先让我直接使用纯生成能力；只有我要求编译、烧录、串口或真实渲染时，
再说明需要启用的本地能力。
```

SkillHub、WorkBuddy、Codex 或其他支持 GitHub Skill 的宿主，均使用宿主自己的 Skill 安装入口。纯生成能力只读取 Skill 文件，不要求 Python、Mind+ 或 OpenSCAD。

下面的源码安装只供开发者或需要本地 CLI 的高级用户使用：

```powershell
git clone https://github.com/Amasun93/ChatMaker.git
Set-Location ChatMaker
python -m pip install -e .
chatmaker-install local
```

`local` 只检查本地生成、硬件和渲染能力，不扫描或修改任何 AI 宿主。可编辑源码安装期间请保留克隆目录；更新源码后再次运行 `chatmaker-install local` 即可。

## 它补上的能力

普通代码生成器通常从一条技术指令开始。小白用户更常见的起点是“我想让课堂有趣一点”“我有一块板子，不知道能做什么”。

ChatMaker 补上四件事。

| 能力 | ChatMaker 怎样处理 |
| --- | --- |
| 创意引导 | 想法模糊时每轮只问一两个问题，再提供两到三套经过筛选的方案 |
| 专业实现 | 把用户选择变成接线、程序、页面、编译、烧录和浏览器操作 |
| 渐进复杂度 | 小白默认看到最少选项，需要更多时才展开样式库和高级游乐场 |
| 真实验证 | 分开报告资料核对、代码编译、固件烧录、串口或浏览器结果和实物效果 |

## 四个创作伙伴

```text
ChatMaker
├─ ChatDuino   硬件、接线、固件、编译、烧录、串口
├─ ChatWeb     前端创作、课堂工具、设备界面、浏览器验证
└─ ChatCAD     参数建模、二维图纸、三维模型、预览与导出
```

### ChatMaker

理解用户想完成的作品，帮助整理目标并选择路线。需要软硬件协作时，它会先约定页面发送什么、设备返回什么，再让两个模块分别实现。

### ChatDuino

帮助用户识别板卡和模块，给出简单直白的文字接线、完整程序和真实编译结果。星核板在 Windows x64 上已可由 ChatMaker 自己准备独立 CLI；Nano、Uno 和经典掌控板暂时仍可复用已有 Mind+。

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

### ChatCAD

先理解用户要固定什么板卡、准备用什么工艺，再从 ChatMaker Knowledge 读取清洗后的机械尺寸。3D 任务默认先讨论并确认任务卡，只有用户明确说“开始生成”才执行；随后优先推荐拓竹 MakerLab，直接返回可粘贴的 OpenSCAD 代码，不生成 STL、预览文件或截图。只有用户不使用 MakerLab，才生成左侧调参数、右侧即时查看的一页式预览实验室。当前 Alpha 支持 Nano、Uno、ESP32 DevKit V1 和星核板，也可生成参数化 DXF、SVG 和 STL。首张“设备与工艺卡”提供 LaserMaker 的黑色切透、红色描线、黄色浅雕、蓝色深雕规则，并将 3 mm 木板设为可调整的默认材料；真实功率和速度必须用具体设备与材料测试后再填写。

```text
帮我给 Arduino Uno 做一个安装底板，边缘留 6 mm，先生成预览实验室让我调整，确认后导出 DXF 和 OpenSCAD。
```

生成成功只代表文件可用，不代表真实孔位和外壳一定合适；第一次加工前仍要用实板试装。

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

V1.0 采用渐进创作流程：先帮助用户跑通最小硬件作品，再按需推荐显示屏、传感器、网页交互、激光切割盒子或 3D 打印外壳。网页和 CAD 不是每个项目的必经步骤。当前主线已覆盖 Nano、Uno、星核板 v4.2.2、经典掌控板 V2.x 和掌控板 3.0；Nano、Uno 与经典掌控板允许把现有 Mind+ 当作后台工具链。当前源码另加入 UNIHIKER M10 Alpha：可识别 M10/K10 分流、生成完整 Python 项目并做 Python 3.7 源码检查，但尚未提供签名知识包或实板运行证据。完整边界见 [V1.0 创作流程合同](https://github.com/Amasun93/ChatMaker/blob/main/docs/contracts/v1-creative-flow.md)。

完整设计见 [ChatMaker 创作伙伴设计](https://github.com/Amasun93/ChatMaker/blob/main/docs/plans/2026-08-14-chatmaker-creative-partner-design.md)。

## 板卡知识怎样按需出现

当前源码构建的 Core 只带运行层、ChatMaker / ChatDuino / ChatWeb / ChatCAD 四个 Skill、7 块板卡、21 种元器件、26 个配方、六个紧凑索引、首批机械资料、schema 与当前案例，不带体积较大的扩展正文。M10 目前只有规范板卡记录、Skill 参考、项目检查器和示例；其签名 Knowledge 知识包尚未发布。这样基础安装更小，也不会把测试或构建缓存交给普通用户。

当 AI 第一次读取某块板卡的详细章节时，`chatmaker-knowledge` 可以按需取得对应知识包并在之后复用。这个动作只安装知识资料，不会安装驱动、Mind+、Arduino Core、Node 或 Chromium。

```powershell
chatmaker-knowledge --request-json '{"action":"section","board_id":"arduino-nano-classic","consumer":"chatduino","section_id":"identify-and-safety"}'
chatmaker-pack status chatmaker-board-arduino-nano-classic-knowledge
chatmaker-pack update chatmaker-board-arduino-nano-classic-knowledge
chatmaker-pack rollback chatmaker-board-arduino-nano-classic-knowledge --version 1.0.0
```

本地实验资料可以放入独立 override 目录，并会明确显示 `provenance=local_override`；它不会伪装成官方内容。完整的缓存、离线、更新和回滚说明见 [安装说明](docs/installation.md)。

## 当前开发状态

| 范围 | 状态 | 已有证据 |
| --- | --- | --- |
| ChatMaker 单入口和三个内部模块结构 | 已验证 | 宿主顶层只有 ChatMaker；ChatDuino、ChatWeb、ChatCAD 在内部独立维护并通过 Skill 格式校验 |
| ChatCAD V1 模式 | 开发版可用 | Chat2D 生成带可调指接榫的六面激光盒、底板拖拽孔位、四色图层、DXF/SVG 和组装预览；Chat3D 生成可旋转的打印外壳及 OpenSCAD/STL；真实试装待用户验证 |
| 创作伙伴对话规则 | 已写入 | 尚需独立前向测试 |
| 数据包和证据状态 | 已验证 | 自动测试与项目 doctor 通过 |
| ChatMaker Knowledge 渐进知识包 | 六板卡已接入 | Nano、Uno、ESP32、星核板、经典掌控板 V2.x、掌控板 3.0 均有独立板卡索引和详细知识包；机械资料仍只对已有机械档案的板卡开放 |
| 主控板自动识别 | 软件流程已实现，待实板 | 本地 CLI 可读取芯片和固件标记；允许时先完整备份，再刷入临时探针并恢复。仍不确定时引导查看丝印或拍正反面照片；三种实体板尚待验收 |
| Nano Mind+ 编译和烧录迁移 | 部分验证 | 原 33 项行为测试已迁移；当前共有 12 个示例从 ChatMaker 路径真实编译；烧录等待有线 Nano |
| Nano/Uno Mind+ 项目流程 | 部分验证 | 独立板型规则、Blink 和 OLED 仪表盘已真实编译；新增连续入口自动检查环境、编译并在有唯一有线端口时烧录，实体板效果等待用户测试 |
<!-- starcore-evidence-summary:start -->
| 星核板独立 CLI | Beta P1 实测 | ChatMaker 管理的隔离工具链已完成准备、地震预警站编译、COM4 上传、硬复位和 115200 串口验证，不要求安装 Mind+ 应用。已有 Mind+ 1.8 或 2 仍可作为兼容后端。此前用户确认中文 OLED、防闪、蜂鸣器与 A/B 键均正常；本轮只重新验证了编译、上传和串口数据。 |
<!-- starcore-evidence-summary:end -->
| DOIT ESP32 DevKit V1 | 部分验证 | 官方 `esp32:esp32@3.3.11` 已安装；`prepare-environment` 真实 no-op 成功；`esp32:esp32:esp32doit-devkit-v1` 已通过 Blink 和 AP 案例真实编译；烧录、启动、串口、SoftAP、HTTP 和实体效果仍待实板 |
| UNIHIKER M10 | Alpha 源码检查可用 | 官方页面已核对 M10 为 Debian/Python 路线、K10 为独立 MCU 路线；板卡记录、完整项目示例和本地项目检查 CLI 已接入，尚未同步到实板或验证屏幕/外设效果 |
| 常用模块、库和示例 | 继续扩充 | 21 种元器件、26 个配方已接入；星核板板载自检现有独立 Recipe，WS2812 与 SG90 课堂示例已真实编译，IDMM-0007 只读诊断、I²C 排错和 OLED 中文分板卡引导已加入 |
| ESP32 AP 手机控制案例 | 部分验证 | `examples/chatweb/esp32-ap-control.html` 是唯一页面源，`chatmaker-web-embed` 生成 `examples/chatduino/esp32/ap-led-sensor/page_html.h`，固件用 `send_P` 和显式长度嵌入页面；浏览器模拟和固件真实编译已通过，硬件仍未验证 |
| ChatWeb 生成和本地预览 | 部分验证 | 一句话可自动获得空间玻璃课堂页、科幻模拟设备台或舞台闪光挑战；仍支持小游戏、ESP32 HTTP 页面和 Nano/Uno Web Serial 控制台，模拟预览不代表硬件已连接 |
| ChatWeb 小游戏 | Alpha 可试玩 | 新增 `mini-game` 路由和反应挑战、躲避收集、拖拽解谜三种单文件模板；默认离线、支持触控，复杂平台与节奏玩法保留为进阶方向 |
| 可执行路由与创意规划 | 已验证 | `chatmaker-route` 返回硬件、网页、组合或澄清路线；`chatmaker-web-plan` 在信息不足时只提问，在信息充分时给出 2–3 条精选方向 |
| 高级方向游乐场 | 显式启用 | 额外方向和 `chatmaker-web-playground` 仅在布尔 `advanced=true` / CLI `--advanced` 时开放 |
| 浏览器自动化 | 已验证 | Chromium 覆盖课堂页、模拟硬件页、ESP32 AP 模拟页和高级游乐场；检查主要交互、390 px 手机布局、至少 44 px 触控目标和零控制台错误 |
| 轻量 Skill 安装 | P0 干净断代 | 基础 Skill 不含 MCP 服务或双宿主扫描；普通安装只安装一个 ChatMaker 入口，执行层统一使用 `chatmaker-*` CLI |
| 串口运行诊断 | 已实现待更多硬件 | `chatmaker-serial` JSONL 会话通过自动测试；星核板实板串口已验证，Nano/Uno 真实日志仍待现场读取 |
| v0.1.0-rc1 发布候选 | 历史发布 | [GitHub 预发布](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc1)；保留其原始产物与当时验证记录 |
| v0.1.0-rc2 发布候选 | 已发布 | [GitHub 预发布](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc2)；rc1 继续保留，rc2 新增串口运行层 |
| v0.1.0-rc3 发布候选 | 已发布 | [GitHub 预发布](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc3)；包含 12 种模块、11 个配方、10 个编译示例和中文资料目录入口 |
| v0.1.0-rc4 发布候选 | 已发布 | [GitHub 预发布](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc4)；新增独立 Uno 适配器、12 个配方、11 个 AVR 编译示例和 18 个 WorkBuddy 工具 |
| v0.1.0-rc5 发布候选 | 已发布 | [GitHub 预发布](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc5)；193 项 Python 测试、4 项 Chromium 自动化、双 ZIP 确定性构建和下载哈希已验证，实物硬件门仍保持未验证 |
| 不依赖 Mind+ 应用的星核板环境 | Beta P1 已验证 | ChatMaker 隔离工具链已完成固定下载校验、地震预警站编译、COM4 上传、硬复位与 115200 串口回读；当前自动准备限 Windows x64 |

## rc5 历史快照

[`v0.1.0-rc5`](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc5) 继续保留，方便回看当时的代码、产物与验证记录，但不再是推荐安装入口。当前体验者应从 GitHub `main` 安装；后续 SkillHub 自动部署属于 Beta P2。

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
chatmaker-avr-project --request-json '{"board_id":"arduino-uno-r3","code":"void setup(){} void loop(){}"}'
chatmaker-starcore --request-json '{"action":"prepare-environment"}'
chatmaker-starcore --request-json '{"action":"doctor"}'
chatmaker-esp32 --request-json '{"action":"prepare-environment"}'
chatmaker-cad --request-json '{"action":"generate","board_id":"arduino-uno-r3","project_name":"uno-base","output_dir":"uno-base"}'
chatmaker-nano-examples --root examples/chatduino/nano
chatmaker-web-plan --brief-json '{"kind":"classroom-tool","idea":"收集课堂反馈","audience_scene":"学生下课前使用","desired_feeling":"清楚而轻松","primary_action":"选择最需要重讲的一步"}'
chatmaker-web-plan --brief-json '{"kind":"mini-game","idea":"做一个小猫接星星的游戏","audience_scene":"学生用手机玩一分钟","desired_feeling":"轻松、有成就感","primary_action":"左右移动小猫接住星星"}'
chatmaker-web-embed examples/chatweb/esp32-ap-control.html examples/chatduino/esp32/ap-led-sensor/page_html.h --symbol CHATMAKER_AP_PAGE
chatmaker-web --request-json '{"kind":"classroom-tool","title":"课堂脉冲","prompt":"今天哪一步最需要再讲一次？","primary_label":"我需要再讲一次","direction_id":"editorial-signal"}' --output examples/chatweb/classroom-pulse.html
chatmaker-web --request-json '{"kind":"mini-game","title":"星光反应赛","prompt":"二十秒内尽可能多地点亮星星。","primary_label":"开始挑战","direction_id":"reaction-rush"}' --output examples/chatweb/my-game.html
chatmaker-web-preview examples/chatweb/classroom-pulse.html
npm ci
npx playwright install chromium
npm run test:browser
```

## 项目结构

```text
skills/       四个创作伙伴的判断方式与工作流程
runtime/      编译、烧录、串口、网页与 CAD 生成等确定性工具
packs/        板卡、模块、案例和视觉方案知识包
examples/     经过验证的完整作品
tests/        自动测试和行为契约
docs/         设计、路线和贡献说明
```

`ChatMaker-Core-<version>.zip` 只包含运行所需部分，不包含上面源码树中的 `tests/`、`knowledge_sources/`、`distribution/` 可选成品或开发缓存。

## 路线

当前按 P0 到 P4 管理：P0 精简与证据归一化已完成；P1 星核板独立 CLI 已完成 Windows x64 最小闭环；P2 将打通 SkillHub 自动部署和 Beta 反馈闭环；P3 再根据真实需求扩展 Nano、Uno、经典掌控板与课堂案例；P4 收口稳定版。

每完成一个阶段，先根据体验者反馈调整下一阶段范围。详见 [ChatMaker Beta 路线图](docs/roadmap.md)。

## License

Apache-2.0
