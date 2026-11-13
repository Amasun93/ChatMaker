# WorkBuddy 联网下载与接线复测

在正常联网的电脑上，让 WorkBuddy 从学生的描述开始，使用 ChatMaker 独立准备工具、编译并烧录到已确认的开发板。先用 Arduino Uno R3 跑一遍，有星核板 v4.2.2、普通 ESP32 或微雪触屏板时再测对应板型。

## 确认实际加载的版本

使用交付时给出的固定 GitHub 文档链接。链接中 `/blob/` 后的 40 位提交号就是复测目标。核对 WorkBuddy 加载的 ChatMaker Skill 来自这个提交里的 `skills/chatmaker/SKILL.md`，并使用同一份源码的本地入口。Windows 本机源码目录为 `D:\Projects\ChatMaker`，在其他目录复测时相应修改 `$Source`。保留现有工作区的改动，使用干净的测试目录切换版本。

在 Windows 把 `$Expected` 填为指定提交号。取回 `main` 后核对 `git rev-parse HEAD`，干净的测试副本可用 `git switch --detach` 切到指定提交。若该电脑还缺 ChatMaker 本地入口，先用同一份源码的 `scripts/setup_local_runtime.ps1` 准备它。

```powershell
$Source = 'D:\Projects\ChatMaker'
$Expected = '填入交付链接里的完整提交号'
git -C $Source fetch origin main
git -C $Source rev-parse HEAD
powershell -NoProfile -ExecutionPolicy Bypass -File "$Source\scripts\workbuddy_preflight.ps1" -SourceRoot $Source -ExpectedRevision $Expected
$CM = Join-Path $Source '.chatmaker-runtime\bin\chatmaker-hardware.cmd'
& $CM --version --expect-revision $Expected --expect-source-root $Source
```

两条检查命令都应返回 `success: true`。保存实际提交号、源码路径和 `source_dirty: false`。Mac 使用同一提交号执行 [Mac 预检和接板步骤](workbuddy-retest-macos.md)。

## 第一次用板和第二次改程序

1. 让 WorkBuddy 使用 `$chatmaker`，告诉它板型和要实现的效果。例如「这是 Uno R3，请让板载灯每秒闪一次，然后帮我下载到这块板」。先用测试板和数据 USB 线，确认实际型号和串口。
2. 用新的板卡工具测试目录测首次准备，记录工具版本、实际来源、换源事件与最终校验。Arduino Uno R3、经典 Nano、Mega 和普通 ESP32 在全新环境通常选择 Arduino CLI `1.6.0`，普通 ESP32 核心通常选择 `3.3.12`。已有可用环境可以继续用兼容版本。星核板使用它自己的兼容工具链。学生无需安装 Mind+、选镜像或先准备离线包。
3. 让 WorkBuddy 把闪灯改快一倍，再观察板上的变化。第二次应复用工具，记录 `installation_performed: false` 或本次没有新增下载事件。
4. 如需复现首选地址失效，可在联网测试会话为一个新的测试目录临时设置 `CHATMAKER_DOWNLOAD_MIRROR_BASE=https://127.0.0.1:9/chatmaker-test`。使用 `--progress jsonl` 记录 `download_switch_source` 和 `download_done`，核对后续仍可取到工具并继续编译。测试完恢复该会话原有镜像设置。

## 接线复测

分别把这两种话交给 WorkBuddy。只问接线时，回复应直接给接线建议或检查结论。

- 「经典 Nano，10 kΩ 电位器还没接，我该怎么接？」应说明三个脚分别怎么连，并给出一个可用的模拟输入脚。
- 「经典 Nano，10 kΩ 电位器两侧接 5V 和 GND，中间已经接 A1，可以吗？」A1 空闲时应允许保留。随后请求生成程序时，代码也应使用 A1。
- 「DOIT ESP32 DEVKIT V1，电位器两侧接 3V3 和 GND，中间接 GPIO25，项目要边开 Wi-Fi 边读电位器，可以吗？」应指出 GPIO25 的模拟读取会与 Wi-Fi 冲突，建议断电后只把中间那根线移到空闲的 ADC1 引脚，例如 GPIO34。

若用微雪 ESP32-S3-Touch-LCD-2.8 复测烧录，先读板背面的 V1 或 V2，再用匹配版本运行屏幕与触摸计时器示例。记录实际能否操作 START、PAUSE、RESET，以及断电后能否再次启动。

回传时附版本预检结果，并分别记录工具下载、编译、烧录、串口和实物效果。没有对应板子的项目填「未测」。
