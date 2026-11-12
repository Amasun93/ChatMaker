# WorkBuddy 复测说明：ChatMaker 0.2.0-beta.5

目标：验证首次准备、国内优先下载、续传、按板安装及编译下载流程。测试前必须确认实际运行的是本版本，不能用旧副本或另一个 CLI 代替。

## 可直接交给 WorkBuddy 的任务

请在 `D:\Projects\ChatMaker` 复测 ChatMaker `v0.2.0-beta.5`。先读本文件和 `skills/chatmaker/SKILL.md`。先通过版本预检，再操作硬件。

不要使用 `C:\Users\<用户名>\ChatMaker`、PATH 中不明来源的 `chatmaker-*`、旧 Release 安装包或旧 Skill 缓存作为本轮执行入口。有未提交代码改动时保留并报告，不执行 reset、clean 或覆盖。不要安装 Mind+，不要修改全局 Arduino15、全局 PATH 或其他项目。

## 1. 获取并确认代码

本机 D 盘由开发者升级完成时，先直接进行下面的预检。另一台电脑或旧 checkout 需要先取得官方代码与标签：

```powershell
git -C D:\Projects\ChatMaker fetch origin --tags
git -C D:\Projects\ChatMaker status --short
git -C D:\Projects\ChatMaker rev-parse 'v0.2.0-beta.5^{commit}'
git -C D:\Projects\ChatMaker rev-parse HEAD
```

两条提交号应完全相同。没有本地改动的测试副本可以切到标签：

```powershell
git -C D:\Projects\ChatMaker switch --detach v0.2.0-beta.5
```

未克隆的电脑从 `https://github.com/Amasun93/ChatMaker.git` 克隆。标签固定本轮测试内容，GitHub main 以后前进也不会改变这次验收对象。

## 2. 准备对应的本地入口

已有正确 runtime 的本机先运行预检；如果报运行时缺失或已安装版本不匹配，再执行环境脚本。这个脚本用于准备 ChatMaker 的 Python/CLI，不是 Arduino 桌面软件：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Projects\ChatMaker\scripts\setup_local_runtime.ps1 -SourceRoot D:\Projects\ChatMaker -RuntimeRoot D:\Projects\ChatMaker\.chatmaker-runtime
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Projects\ChatMaker\scripts\workbuddy_preflight.ps1 -SourceRoot D:\Projects\ChatMaker
```

只有 `success: true` 才进入后续测试。保存返回的完整 `expected_revision` 与 `runtime`。它会检查：

- 源码路径是 D 盘目标仓库，提交号等于本次标签，源码工作区干净。
- 源码版本和 Python 安装元数据都是 `0.2.0b5`。
- Python 与 runtime 都来自本轮指定目录。

缺少标签先 fetch；安装版本不符重跑上面的环境脚本；路径或提交不符时先解决版本问题，不能继续测完后才补记。

以后统一使用以下明确入口，不依赖 PATH：

```powershell
$CM = 'D:\Projects\ChatMaker\.chatmaker-runtime\bin\chatmaker-hardware.cmd'
& $CM --version
```

常用动作采用普通参数。复杂请求保存为 UTF-8 JSON 文件，再用 `--request-file`；也可用 `--request-json -` 从标准输入读取。不要把带引号的复杂 JSON 直接塞进 `.cmd` 参数。

Windows PowerShell 5.1 向原生命令传递管道文本时，默认编码可能丢失中文。优先使用 `--request-file`；必须使用管道时，先将本次会话的 `$OutputEncoding` 设为 `New-Object System.Text.UTF8Encoding $false`，并用 `Get-Content -Raw -Encoding utf8` 读取请求文件。

## 3. 先验证计划不写入、不下载

```powershell
& $CM --action prepare-environment --board-id nova-esp32 --library U8g2 --dry-run --progress none
& $CM --action prepare-environment --board-id waveshare-esp32-s3-touch-lcd-2-8 --revision v1 --dry-run --progress none
```

核对 `components`、`archive_bytes`、`remaining_download_bytes`、`policy_blockers`。经典 ESP32 只应包含 `esp32-libs`，S3 只应包含 `esp32s3-libs`；均不应准备其他芯片 SDK、RISC-V 编译器或调试器。当前配置面向常规 Arduino 编译和 USB 下载；ULP、JTAG、其他芯片不是此最小配置的能力声明。

没有稳定测速数据时，预计时间可以为空，不要求工具编造剩余分钟数。

`--dry-run` 只支持环境准备、环境检查和端口查询；与 `run`、`compile` 或 `compile-upload` 组合时必须返回 `dry_run_unsupported_action`，不执行这些动作。

## 4. 测试首次准备与缓存复用

```powershell
& $CM --action prepare-environment --board-id nova-esp32 --library U8g2 --progress jsonl
& $CM --action prepare-environment --board-id nova-esp32 --library U8g2 --progress jsonl
```

第一次缺少组件时应自动补齐；第二次应返回 `installation_performed: false`，并且不重复下载。检查下载来源和最终校验结果。进度事件在 stderr，最终结果是 stdout 的一个 JSON 对象；宿主不支持进度卡片时直接显示文字即可。

默认策略是国内优先，ESP32 大组件从乐鑫国内地址下载。CLI、Arduino 辅助工具、U8g2 目前保留官方直连地址。`--download-policy domestic-only` 是额外的严格策略：缺少已验证国内源的组件必须明确停止，或使用已校验缓存/组织提供的 HTTPS 镜像，不能悄悄访问境外。

要测真正的空白环境，请使用另一台干净电脑，或显式创建新的测试 runtime：

```powershell
$Fresh = 'D:\ChatMakerTests\beta5-fresh'
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Projects\ChatMaker\scripts\setup_local_runtime.ps1 -SourceRoot D:\Projects\ChatMaker -RuntimeRoot $Fresh
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Projects\ChatMaker\scripts\workbuddy_preflight.ps1 -SourceRoot D:\Projects\ChatMaker -RuntimeRoot $Fresh
$CM = Join-Path $Fresh 'bin\chatmaker-hardware.cmd'
```

不要删除已有缓存来制造“首次安装”；使用独立目录。报告说明是否复用了项目内旧缓存、系统 Python 或已有网络代理。仅设置一个新目录不等于整台电脑零环境。

## 5. 测试中断与恢复

在新 runtime 的大组件下载期间结束本次准备进程，再执行同一命令。观察 `download_start.resume_from` 是否大于 0，最终是否 `verified: true`。已完成的缓存应复用，部分文件保留为 `.part` 和 `.part.json`。

先记录文件名和中断前字节数。不要手工拼接不同版本，也不要改 `.part.json` 来伪造已下载状态。源不支持 Range 时允许安全重启该文件，并应如实记录；本地受控 HTTP 用例另覆盖错误范围、损坏文件和换源。

## 6. Nova + OLED

`nova-esp32` 仅用于已确认的 ESP32-D0WD-V3、4 MB Flash 配置。CH340 本身不能证明板型。屏幕例程是 SSD1306、128×64、I2C 地址 0x3C、SDA21/SCL22；如果实物屏幕控制器或接线不同，先核对，不直接套用。

```powershell
$Sketch = 'D:\Projects\ChatMaker\examples\chatduino\nova-oled-hello'
& $CM --action prepare-environment --board-id nova-esp32 --sketch $Sketch
& $CM --action compile --board-id nova-esp32 --sketch $Sketch
& $CM --action ports --board-id nova-esp32
```

确认目标板型和实际串口后，再执行以下命令，替换 `COMx`：

```powershell
& $CM --action run --board-id nova-esp32 --sketch $Sketch --board-confirmed --port COMx
```

观察中文“你好”，记录 `NOVA_OLED_HELLO_DONE`，断电重启后再观察。例程会重复打印运行标记，串口晚打开也可以读取。上传成功、串口标记出现、屏幕正常三项分别记录。

## 7. 微雪 ESP32-S3 触屏板

软件测试可以分别编译 V1/V2；烧录前必须读背面标签，使用对应版本。不能因为手头不知道版本就随便挑一个驱动。

```powershell
$Board = 'waveshare-esp32-s3-touch-lcd-2-8'
$Revision = 'v1' # 按实物标签改为 v1 或 v2
$Screen = 'D:\Projects\ChatMaker\examples\chatduino\waveshare-s3\screen-diagnostic'
$Timer = 'D:\Projects\ChatMaker\examples\chatduino\waveshare-s3\classroom-timer'
& $CM --action prepare-environment --board-id $Board --revision $Revision
& $CM --action compile --board-id $Board --revision $Revision --sketch $Screen
& $CM --action compile --board-id $Board --revision $Revision --sketch $Timer
```

连接数据 USB、确认实物型号和版本后，用 `--action run ... --board-confirmed --port COMx` 下载。检查屏幕、START/PAUSE/RESET 触摸、USB 重连和断电重启。没有实板就填写“未测”，不要把编译通过写成这些项目通过。

## 8. 反馈格式

请把报告保存到项目源码以外的测试目录，至少提供：

| 项目 | 记录内容 |
| --- | --- |
| 版本 | 预检 JSON、完整提交号、源码/入口/runtime 路径 |
| 条件 | Windows 版本、网络、代理、板型、V1/V2、驱动和串口 |
| 首次准备 | 每阶段耗时、是否复用缓存、实际来源、失败与自动恢复 |
| 体积 | 实际网络接收字节、压缩包缓存、解压工具占用分别记录 |
| 重复运行 | 是否重复下载、环境检查和编译耗时 |
| 中断续传 | 组件、中断位置、恢复偏移、最终大小和校验结果 |
| 效果 | 编译、上传、串口、屏幕、触摸、断电重启分别填通过/失败/未测 |
| 仍需手工处理 | 每次手工命令及原因，不能只写“最后成功” |

固定测试网络下争取首次十分钟内完成；时间不作为所有网络的保证。完整准备后，同版本再用应不重复下载。出现问题时保留 JSON、进度日志和缓存，不先安装 Mind+ 或换另一份 ChatMaker 来绕过。
