# UNO R4 WiFi、XIAO ESP32S3 与行空板 K10 验证记录

2026-11-18。四个板型统一从 `chatmaker-hardware` 选择目标。Wiki 和接线讨论可以直接读本地资料。实际编译与下载使用 ChatMaker 准备的 Arduino CLI 工具，不需要安装 Mind+ 或 Arduino IDE。

| 板型 | 首跑示例 | 写入后应观察到的结果 |
| --- | --- | --- |
| `arduino-uno-r4-wifi` | [点阵心跳](../../examples/chatduino/uno-r4-wifi/matrix-heart) | 板载点阵每秒闪出一颗心。串口重复打印板卡标记。 |
| `seeed-xiao-esp32s3` | [USB 小灯](../../examples/chatduino/xiao-esp32s3/usb-blink) | 用户灯短闪一次，串口每秒打印板卡标记。 |
| `seeed-xiao-esp32s3-sense` | [相机单帧检查](../../examples/chatduino/xiao-esp32s3-sense/camera-check) | 115200 串口约每三秒打印一次 `frame_bytes`。用普通物品遮挡或移开镜头观察是否持续抓到数据。 |
| `unihiker-k10` | [板载三灯](../../examples/chatduino/unihiker-k10/board-rgb) | 三颗板载灯依次亮起，串口每轮打印一次板卡标记。 |

USB 端口可能随板子重启变化。先看丝印和套件确认板型，再通过拔插确认哪个端口随这块板消失和重新出现。遇到通用 ESP32 USB 串口时，给 ChatMaker 传入已经确认的端口。Sense 和普通 XIAO 共用编译目标，各自有板卡条目和示例。

## WorkBuddy 复测

1. 打开交付时给出的固定 GitHub 链接，取 `/blob/` 后的 40 位提交号。让 WorkBuddy 更新并重新加载 ChatMaker。运行 `chatmaker-hardware --version`，核对 `source_commit` 和 `source_root`，确认 Skill 跟命令来自同一份源码。版本号一样时也比较提交号。源码目录可以用 `python scripts/workbuddy_preflight.py --expected-revision <完整提交号>` 检查。
2. 让它按手上板型读取 `start-here`、接线和常见问题。先看它能否分清 R4 WiFi、普通 XIAO、Sense 和 K10。检查接线时重点看 R4 的 3.3 V Qwiic、Sense 的 SD 共用引脚，以及 K10 的 Gravity 口。
3. 让它预览当前板型的准备工作，缺组件时再准备。编译上述例子，记录 `compile.fqbn`、工具版本、固件产物以及是否复用缓存。K10 和 UNO R4 WiFi 首次需要各自的核心，XIAO 两版复用同一个 ESP32-S3 环境。
4. 已连接且已确认是本次目标的板子才写入。请 WorkBuddy 用 `run` 继续，通过它传入板型和实际 USB 端口。之后用 115200 查看示例串口，观察板载灯或相机，再断电重启复查。

> WorkBuddy 提示词：先检查我当前加载的 ChatMaker 来自哪个目录、哪个 Git 提交，和 GitHub 上这份复测说明的提交对齐。我用的是【填精确板型】。查它的本地 Wiki，告诉我哪些接口用起来会冲突，然后预览并准备该板所需工具，编译它的第一个示例。等你确认板型和 USB 端口后直接烧录，不走 Mind+。分别告诉我编译、烧录、串口和我应该看到的效果。

## 证据范围

- Windows x64 四个示例均通过 ChatMaker 的编译入口生成固件，使用 Arduino CLI 1.3.1、Renesas 1.6.0、缓存的 Arduino-ESP32 3.3.11 和 DFRobot K10 0.0.5。自动测试检查上传参数和端口选择。真板写入、串口、断电重启与实体效果待复测。
- Apple 芯片与 Intel Mac 的工具选择由测试覆盖，两种 Mac 的真实编译由 GitHub Actions 硬件编译工作流验证。真板验证按上面的步骤单独记录。

Windows 上如果旧版厂商编译器报路径太长，可以把 `CHATMAKER_RUNTIME_ROOT` 指向更短的本地目录后重新准备工具。原有课程工程可以留在自己的目录。
