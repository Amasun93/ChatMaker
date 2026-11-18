# ChatMaker 有什么新变化？

这是面向老师、学生和体验者的公开更新记录。最新更新放在最上面，标明日期和对应的版本标签或主分支提交。

## 2026-11-18 · 主分支新增 UNO R4 WiFi、XIAO ESP32S3 和行空板 K10

- 四个板型可通过 ChatMaker 自己准备工具、编译和 USB 烧录，无需 Mind+。XIAO 普通版和带摄像头的 Sense 分别提供板卡条目和示例。
- 各板卡新增八节 Wiki，覆盖板型识别、接线复核、共用引脚、首次准备和常见问题。先读资料，需要编译时再预览并准备工具。[板卡 Wiki](knowledge_sources/published/boards)
- 课堂示例从 UNO R4 WiFi 点阵心跳、XIAO 小灯、Sense 单帧检查、K10 板载三灯开始。软件检查和真板观察分开记录。[验证与 WorkBuddy 复测](docs/verification/2026-11-18-classroom-boards.md)

## 2026-11-18 · 补齐板卡 Wiki 与新板接入流程

- 为 Arduino Mega 2560、ESP32-C3-DevKitM-1、ESP32-C6-DevKitC-1、ESP32-S3-DevKitC-1 N8R8 和行空板 M10 补齐八节 Wiki。老师和学生可以直接查板型、接线、工具、例子和常见问题。[板卡 Wiki](https://github.com/Amasun93/ChatMaker/tree/main/knowledge_sources/published/boards)
- 完整源码可直接读取所有已登记板卡的 Wiki。Skill 安装包附带全部板卡的速查说明。新增板卡的提交会检查 Wiki 和读取入口是否齐全。[新板接入流程](docs/contributing/board-research-workflow.md)

## 2026-11-18 · 微雪 2.8 触屏板 Wiki 和 V2 识别

- 补齐微雪 ESP32-S3-Touch-LCD-2.8 的八节板卡 Wiki。源码可直接读取，安装 Skill 的用户可查随包的板卡速查说明。[板卡 Wiki](knowledge_sources/published/boards/waveshare-esp32-s3-touch-lcd-2-8/start-here.md)
- 搜索可识别完整名称加 V2 / CST3530，以及「微雪 2.8 V2」。2.8B、2.8C 不再被识别为这块 2.8。首次编译可预览还需下载什么，已准备的项目可复用缓存。

## 2026-11-18 · 主分支课堂回答与更新时间建议

- 「说人话」随 ChatMaker 安装。回答先给学生能照做的一步和该观察的结果，保留具体引脚、电压、尺寸和验证结果。学生想学原理、老师要备课或需要深入排错时，再展开讲。
- 发现新版时，ChatMaker 会根据变化和当前任务判断现在更新是否有帮助。能解决眼前卡点时会提出更新建议。可能需要重新下载工具或耽误课堂时，通常建议先做完当前任务。[检查和更新说明](docs/installation.md#检查和更新-chatmaker)

## 2026-11-18 · 主分支更新检查与 Python 环境准备

- 会话第一次使用 ChatMaker 时，会尝试后台检查版本。项目可以立即开始。发现新版后会说明更新内容，等用户同意才更新。[检查和更新说明](docs/installation.md#检查和更新-chatmaker)
- 编译、烧录等操作先复用可用的项目环境，其次用电脑上兼容的 Python。找不到或无法创建可用环境时，才使用便携 Python。源码安装支持兼容的 CPython 3.11 或更高版本，Windows 预编译 Core 包仍使用 CPython 3.11 x64。
- 便携 Python 按 Windows x64、Apple 芯片和 Intel Mac 选择，并校验下载大小与 SHA-256。Mac 的便携包适用于 macOS 12 及以上，实际安装流程待双架构 Mac 复测。[Mac 复测说明](docs/verification/workbuddy-retest-macos.md)

## 2026-11-13 · 主分支新增版本自检和更新入口

- 可以直接对 ChatMaker 说「检查更新」，核对正在用的 Skill 和本地工具。版本号相同时也能按提交和文件内容检查。GitHub 查询失败时会试 Gitee，并给出实际来源与更新日志。
- 说「更新 ChatMaker」可以更新官方源码的主分支。通过 AI 应用安装的 Skill 走该应用的更新入口。更新后重新加载并自检，再继续 Demo。[安装与升级说明](docs/installation.md#检查和更新-chatmaker)

## 2026-11-13 · 0.2.0-beta.6 之后的主分支更新

这次更新对应 [提交 `fc44ec5`](https://github.com/Amasun93/ChatMaker/commit/fc44ec5b5d582daa3c427990c9b4b968d1e5f65b)。

- 首次用板时，ChatMaker 只准备这块板需要的工具。下载地址太慢或连不上时会尝试备用来源。支持续传的文件可以接着下载，已经验证过的工具下次直接复用。
- Uno R3、经典 Nano、Mega 2560 和已适配的 ESP32 板型可用独立工具完成编译和烧录。星核板 v4.2.2 在 Windows x64 上也由 ChatMaker 自己准备编译器、烧录工具和字库，无需安装 Mind+。
- Apple 芯片和 Intel Mac 都已通过 Arduino 和 ESP32 的课堂示例编译。微雪 ESP32-S3-Touch-LCD-2.8 的 V1 和 V2 屏幕、触摸计时器示例也已编译通过，实板烧录、触摸和断电重启待复测。[Mac 编译记录](https://github.com/Amasun93/ChatMaker/actions/runs/43394333622)
- 还没接线时可以请 ChatMaker 推荐引脚。已经接好时，把板型和接法告诉它。安全可用的线可以保留，有冲突时会指出具体要改哪根线。
- 用 WorkBuddy 试用时，先核对实际加载的 Skill 和本地工具对应的提交，再试一次写入程序和一次修改。[固定到本次提交的复测说明](https://github.com/Amasun93/ChatMaker/blob/fc44ec5b5d582daa3c427990c9b4b968d1e5f65b/docs/verification/workbuddy-retest-download-sources.md)

## 2026-11-12 · 0.2.0-beta.6

- 包含 beta.5 的国内下载、按板准备、独立编译及版本预检升级。
- 修正 GitHub 全新 Windows 环境下长路径与 DOS 短路径别名的测试夹具，目录比较使用同一真实路径；硬件运行逻辑保持经实际编译验证的实现。
- 修复 Gitee 镜像处理带说明标签时的重复推送问题，恢复 GitHub 原始标签对象后再同步，不覆盖远端标签。
- WorkBuddy 本轮复测固定为 beta.6，保留已经发布的 beta.5 标签。

## 2026-11-12 · 0.2.0-beta.5

- 经典 ESP32 和微雪 S3 共用独立环境准备，不要求预装 Mind+ 或 Arduino IDE；只准备当前芯片所需的核心、编译和烧录组件。
- ESP32 大组件接入乐鑫国内下载地址，固定版本和校验值。下载中断可继续，失败限次重试、换源，并显示准备、下载、校验、解压、编译和烧录阶段。
- 修复新版 Arduino CLI 清单格式不兼容。常用动作可以直接传参数，复杂请求使用文件或标准输入，减少 Windows 引号问题。
- 加入当前代码路径、提交号、安装版本与 runtime 信息，以及 WorkBuddy 版本预检和复测说明，避免测到另一个旧副本。
- 微雪 V1/V2 软件适配随本轮同步；新增明确选择的 Nova 经典 ESP32 配置与 OLED 中文例程。实板、屏幕和触摸效果继续单独验收。

## 2026-11-10 · 开发记录（随 0.2.0-beta.5 同步）

- 支持独立工具链的板卡优先走“写好代码 → 准备必要工具 → 编译 → 接板下载”的连续流程，不再因为缺少 Mind+ 而要求安装它。
- 加入微雪 ESP32-S3-Touch-LCD-2.8，分别处理 V1 和 V2 的触摸芯片；两版屏幕诊断、课堂计时器都已实际编译通过。
- 已校验的工具可以重复使用；准备或编译失败时保留当前项目和错误，不切换到无关的软件安装路线。
- 当前完成到软件和编译阶段。开发板版本确认、实物下载、触摸、断电重启以及 WorkBuddy 真实会话验收仍待进行，不能据此宣称培训现场已经跑通。

## 2026-08-26 · 0.2.0-beta.4

### 新增两款硬件支持

- 掌控板 3.0 完成首阶段接入，Windows 电脑可直接准备开发环境并编译程序。
- 新增自研星辰板与 1.3 寸 OLED 支持，已完成程序下载、运行、显示和断电重启验证。
- 新增 micro:bit V2 入门资料，方便后续直接接板测试和使用。
- 完善板卡资料与接入规范，尺寸、兼容范围和实物验证状态更加清晰。

## 2026-08-26 · 0.2.0-beta.3

### 硬件支持持续扩展

- 优化板卡和模块的维护方式，后续支持新硬件更快、更稳定。
- 完善多款板卡的尺寸资料，为安装结构和外壳设计做好准备。
- 完成 micro:bit V2 的前期适配，拿到实板后将继续验证。
- 星核板核心开发流程已完成复测。

## 2026-08-26 · 0.2.0-beta.2

### 经典掌控板不再要求先装 Mind+

- **Windows x64 独立链可用了**：经典掌控板 V2.x 现在可以由 ChatMaker 自己准备固定工具、检查环境、编译、安全选择端口、上传、复位和读取串口；电脑里已有 Mind+ 1.8 或 2 仍可继续使用。
- **中文案例已真实编译**：新增静态中文状态页，屏幕只绘制一次，循环中不反复清屏，尽量避免明显闪烁。
- **实板结果没有提前写成功**：当前只验证到环境、源码和编译；由于没有确认连接的是经典掌控板，上传、串口、断电重启和 OLED 肉眼显示仍待实板验收。
- **micro:bit V2 已完成官方路线比较**：默认建议从 MicroPython 打包 + DAPLink U 盘烧录 + 115200 串口开始，MakeCode 编译作为下一层；CODAL/pyOCD 保留给高级原生开发和调试。

## 2026-08-26 · 0.2.0-beta.1

### 这次最重要的变化

- **ChatMaker 更精简了**：只保留一个 ChatMaker 入口，ChatDuino、ChatWeb 和 ChatCAD 在内部配合，不再要求额外配置旧 MCP。
- **星核板不用先安装 Mind+ 了**：在 Windows x64 上，ChatMaker 可以自己准备环境、编译、上传并读取串口。电脑里已有 Mind+ 1.8 或 2 也仍然可以使用。
- **证据说得更准确了**：编译、上传、串口和实物效果分开记录，不会再把“程序上传成功”写成“屏幕或蜂鸣器一定正常”。
- **版本更容易看懂了**：当前是 Beta 体验版；以后每次重要更新都会在这里用大白话说明。

### 如何更新？

如果你通过 GitHub 链接安装，请继续使用：

```text
https://github.com/Amasun93/ChatMaker
```

如果已经安装旧版，请让你使用的 AI 或 Skill 管理器从这个仓库重新更新。
