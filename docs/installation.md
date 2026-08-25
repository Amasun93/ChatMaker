# ChatMaker 安装与升级说明

## 普通学生：只安装一个 Skill

在 WorkBuddy、Codex、SkillHub 或其他支持 GitHub Skill 的应用中，使用应用自己的 Skill 安装入口安装：

```text
https://github.com/Amasun93/ChatMaker
```

安装完成后只使用 `$chatmaker`。ChatDuino、ChatWeb、ChatCAD 是 ChatMaker 内部的三个专业模块，不是另外三个需要学生安装或配置的入口。

纯生成能力可以直接使用，包括创意引导、网页代码、硬件接线与程序草稿、OpenSCAD 代码。普通安装不会扫描 Codex、WorkBuddy 或其他 AI 应用，也不会安装额外的工具服务。

## 从旧版做一次干净升级

旧版曾经注册过 ChatMaker MCP 的用户，建议按下面顺序做一次断代升级：

1. 在 WorkBuddy 的 MCP 设置中删除旧的 `chatmaker` 项；如果 `arduino-nano-mindplus` 明确指向旧 ChatMaker 服务，也一并删除。
2. 退出并重新启动 WorkBuddy。
3. 删除旧 ChatMaker Skill，再通过原生 Skill 安装入口安装新版。
4. 确认顶层只显示一个 ChatMaker 入口。

源码用户可以先预览再清理一个明确的配置文件。脚本不会搜索任何宿主，也不会删除名称相同但命令不属于旧 ChatMaker 的第三方服务：

```powershell
python scripts/cleanup_legacy_mcp.py --config "$env:USERPROFILE\.workbuddy\.mcp.json" --dry-run
python scripts/cleanup_legacy_mcp.py --config "$env:USERPROFILE\.workbuddy\.mcp.json"
```

如果 WorkBuddy 显示的配置路径不同，把 `--config` 后面的路径换成设置页显示的实际路径。执行清理时会先在原目录生成带时间戳的备份。

## 需要编译、烧录、串口或真实渲染时

本地执行统一使用 `chatmaker-*` CLI。源码开发者可以运行：

```powershell
git clone https://github.com/Amasun93/ChatMaker.git
Set-Location ChatMaker
python -m pip install -e .
chatmaker-install local
```

`chatmaker-install local` 只读检查操作系统、Python、终端、浏览器、串口、Mind+ 和 Arduino CLI。它不读取或写入 AI 宿主配置，返回值包含 `host_scan_performed=false`。

常用入口：

```powershell
chatmaker-starcore --request-json '{"action":"doctor"}'
chatmaker-nano --request-json '{"action":"doctor"}'
chatmaker-uno --request-json '{"action":"doctor"}'
chatmaker-esp32 --request-json '{"action":"doctor"}'
chatmaker-unihiker --request-json '{"action":"check_project","project":"<project-folder>"}'
chatmaker-serial
chatmaker-cad --request-json '{"action":"openscad-status"}'
```

AI 工作区如果具备本地命令执行能力，就直接调用这些 CLI；不再维护第二套 MCP 调用名称。

## Mind+ 版本策略

- 电脑已经有可用的 Mind+ 1.8.x：直接复用。
- 电脑已经有可用的 Mind+ 2.x：直接复用。
- 两个版本都可用：优先使用 Mind+ 2.x。
- 两个版本都没有：在星核板独立工具链完成前，推荐安装已经验证的 Mind+ 1.8.x。
- 不会让已经有可用 Mind+ 的学生再下载另一套版本。

星核板 Mind+ 2.x 的已验证配置为：

```text
Arduino CLI: E:\Mind+2\applications\deps\mind-link\tool\arduino-cli.exe
Config: C:\Users\asus\AppData\Local\mind+\Arduino\arduino-cli.yaml
FQBN: mindplus:esp32:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none
```

Mind+ 1.8.x 回退目标为：

```text
dfrobot:mpython:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none
```

## 可选择的运行环境位置

受信任的 Core bootstrap 默认把运行环境放在当前项目的隐藏目录：

```text
<项目目录>\.chatmaker-runtime\
```

也可以显式选择其他磁盘或目录：

```powershell
Get-FileHash .\ChatMaker-Core-0.1.0-rc5-windows-amd64.zip -Algorithm SHA256
Get-Content .\ChatMaker-Core-0.1.0-rc5-windows-amd64.zip.sha256
python .\trusted-bootstrap\bootstrap.py `
  --archive .\ChatMaker-Core-0.1.0-rc5-windows-amd64.zip `
  --checksum .\ChatMaker-Core-0.1.0-rc5-windows-amd64.zip.sha256 `
  --release-manifest .\ChatMaker-Core-0.1.0-rc5-windows-amd64.zip.manifest.json `
  --release-signature .\ChatMaker-Core-0.1.0-rc5-windows-amd64.zip.manifest.json.sig.json `
  --project-root . `
  --install-root E:\ChatMakerRuntime
```

bootstrap 会在用户目录保存轻量位置记录 `.chatmaker-location.json`，其中不含程序主体、密码或密钥。

- 项目和 `.chatmaker-runtime` 一起移动：launcher 按自身新位置继续工作。
- 项目被移动但隐藏目录没有一起移动：在新项目目录重新运行 bootstrap，重建环境并刷新位置记录。
- 项目或运行目录被删除：重新取得已验证的发布文件，再运行 bootstrap；不要依赖已经失效的位置记录猜测文件仍然存在。

本轮没有把完整便携 Python、OpenSCAD 或国内 CDN 打进仓库。后续课堂运行包应使用独立的版本化压缩包或对象存储，附 manifest、SHA-256、大小、版本和许可证记录；不建议把几十兆二进制直接提交到 Git 历史。

## OpenSCAD 边界

生成 OpenSCAD 代码不要求本机安装 OpenSCAD；本地真实渲染或导出 STL 才需要。检查命令为：

```powershell
chatmaker-cad --request-json '{"action":"openscad-status"}'
```

自动安装必须先取得用户明确同意，随后才可运行：

```powershell
chatmaker-cad --request-json '{"action":"openscad-prepare","allow_install":true}'
```

当前 P0 仍使用官方 WinGet 包 `OpenSCAD.OpenSCAD`。国内镜像、便携 OpenSCAD 和最小 Python 运行包属于后续独立部署任务；安装 OpenSCAD 只能解决“缺少渲染器”，不能修复几何代码本身的错误。

## 版本检查接口边界

版本检查是只读动作，只能返回：

- `current_version`
- `latest_version`
- `update_available`
- 来源、下载页和变更摘要

当 `update_available=true` 时，必须先询问用户：“发现新版本，是否更新？”只有用户明确回答同意，更新动作才可以下载或覆盖文件。启动 ChatMaker 不等于授权更新；不得静默强制覆盖。

GitHub Actions 到 SkillHub 的自动发布、国内 CDN 和自动分发不属于本轮 P0。

## 无 MCP 的星核板代表路径

只做环境检查和真实编译：

```powershell
python scripts/verify_no_mcp_starcore.py
```

在板卡身份、端口和固件覆盖都已确认安全时，才增加上传与串口：

```powershell
python scripts/verify_no_mcp_starcore.py `
  --upload `
  --port COM4 `
  --serial-marker STARCORE_SELF_TEST_READY
```

脚本直接调用 `chatmaker.hardware.starcore` 和 `chatmaker.hardware.serial_monitor`。这证明本地脚本本身能完成相应动作；某个 AI 应用能否触发它，取决于该应用是否允许执行本地命令。

## 证据边界

环境发现、源码生成、编译、上传、复位、串口、浏览器交互和实体效果分别记录。命令退出码不能自动升级为实物效果。

<!-- starcore-install-evidence:start -->
Mind+ 1.8 和 2 均可作为星核板后端，优先复用电脑里已有的可用版本；两者都有时当前适配器默认选 2。本次 Mind+ 2 已用于自检和 OLED 案例的编译、COM4 上传、硬复位与 115200 串口验证。用户此前确认自检蜂鸣器真实发声；最新运行没有重新听音。

`BUZZER_COMMAND_COMPLETE` 只对这块已确认健康的板和这个已知自检程序构成约定的课堂代理证据。OLED 已由用户确认实际显示成功；后续中文内容仍要确认字库，动态页面应减少整屏清空和无意义刷新。按键动作、CAN、断电重启和其他模块继续分别验收。
<!-- starcore-install-evidence:end -->
