# ChatMaker P0：无 MCP 星核板路径验证

日期：2026-08-25

板卡：IDMC-0001 星核板 v4.2.2

目标：证明本地脚本/CLI 能力不依赖 WorkBuddy MCP 注册。

## 可复现命令

只做环境检查与真实编译：

```powershell
python scripts/verify_no_mcp_starcore.py
```

在已确认板卡身份、端口唯一且允许覆盖当前固件时，增加上传与串口标记：

```powershell
python scripts/verify_no_mcp_starcore.py `
  --upload `
  --port COM4 `
  --serial-marker STARCORE_SELF_TEST_READY
```

脚本会清除 WorkBuddy/MCP 相关环境变量，通过 `python -m chatmaker.hardware.starcore` 和 `python -m chatmaker.hardware.serial_monitor` 调用本地运行层。它不读取或写入任何 MCP 配置，并返回 `mcp_registration_used=false`。

## 本次结果

- doctor：成功；选择 `mindplus-2-cli`。
- Arduino CLI：`E:\Mind+2\applications\deps\mind-link\tool\arduino-cli.exe`。
- 配置：`C:\Users\asus\AppData\Local\mind+\Arduino\arduino-cli.yaml`。
- FQBN：`mindplus:esp32:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none`。
- Core：`mindplus:esp32@0.0.1`。
- 编译：`onboard-self-test` 成功；程序 242324 bytes，动态内存 17820 bytes。
- 端口：COM4 是唯一合格的非蓝牙有线端口。
- 上传：成功；ESP32D0WDQ6 revision 3，16 MB Flash，四段写入均 `Hash of data verified`，随后 `Hard resetting via RTS pin`。
- 串口：115200 成功打开，匹配 `STARCORE_SELF_TEST_READY`，并收到 `BUZZER_COMMAND_COMPLETE`、按钮状态和持续三轴加速度数据。
- 聚焦自动测试：40 项通过，覆盖 Mind+ 2 优先/1.x 回退、无宿主扫描的 `local` 模式、基础 Skill 只使用 CLI、旧注册定向清理、OpenSCAD CLI 路由和知识接口；另有发布/Bootstrap 与两条干净 Core 集成路径通过。

## 证据边界

1. 上述命令证明脚本本身可完成环境检查、编译、上传和串口，不证明任意 WorkBuddy 安装都自动拥有本地命令执行权限。
2. WorkBuddy、Codex 或其他 AI 工作区只有在具备本地命令执行能力时，才能触发同一 `chatmaker-*` CLI；ChatMaker 不再发布第二套 MCP 入口。
3. 本轮串口证明程序启动并输出自检数据，用户也在同一硬件复验中确认蜂鸣器真实发声。用户随后明确同意：对这块已确认健康的板和这个已知自检程序，今后可把 `BUZZER_COMMAND_COMPLETE` 作为课堂代理证据。这个约定不能推广到其他板卡、程序或物理效果。
4. 当前板上运行的是 `onboard-self-test`。命令成功不自动证明其他外接模块、CAN、断电重启或后续作品的实体效果。
