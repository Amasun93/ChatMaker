---
schema_version: "1.0"
kind: knowledge-page
stable_id: idmc-0001-starcore-v4-2-2-toolchains-and-upload
board_id: idmc-0001-starcore-v4-2-2
section_id: toolchains-and-upload
source_refs:
  - source-idmc-0001-starcore-v4-2-2-owned-docs
---
# Mind+、编译和上传

<!-- starcore-evidence-summary:start -->
## 当前结构化证据摘要

ChatMaker 管理的独立 CLI 是星核板首选后端；它在隔离目录中使用固定 Arduino CLI、`mindplus:esp32@0.0.1` 核心、六个校验过的 mPython/OLED 库，以及 Mind+ 国内官方设备包中经过 SHA-256 校验的中文字库，不要求安装 Mind+ 应用。上传前检查 Flash `0x400000` 的 `GUIX` 标记，仅在缺失时写入字库。Mind+ 1.8 和 2 仍是可用的兼容后端，两者都有时兼容路线默认选择 2。

2026-08-26，独立链路用桌面地震预警站完成真实编译、COM4 上传、RTS 硬复位和 115200 串口回读，看到 `STARCORE_QUAKE_STATION_UI_V2_READY` 与连续 `QUAKE_DATA`。此前用户已确认中文 OLED、防闪、蜂鸣器、A/B 键和预警效果均正常；本轮没有重新肉眼或听觉确认这些实体效果。

权威状态读取 `packs/boards/idmc-0001-starcore-v4-2-2.yaml`、`packs/recipes/starcore-onboard-self-test.yaml` 和 `packs/recipes/starcore-idmd-0021-oled-message.yaml`；本段由 `scripts/sync_starcore_evidence.py` 生成。
<!-- starcore-evidence-summary:end -->

ChatMaker 管理的独立 CLI 是当前首选后端。在 Windows x64 上先运行 `prepare-environment`，它会把固定 Arduino CLI、`mindplus:esp32@0.0.1` 核心和六个 mPython/OLED/中文字库安装到 ChatMaker 的隔离目录，不要求安装 Mind+ 应用。Mind+ 1.8 和 2 仍是已验证的兼容后端；两者都可用时兼容路线默认使用 2。Mind+ 2 目标为 `mindplus:esp32:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none`，Mind+ 1.8 目标为 `dfrobot:mpython:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none`，不能混用路径和上传参数。

生成程序前先列出需要添加的 Mind+ 扩展，再给完整 Arduino/C++ 程序。常规程序包含 `MPython.h`；模块额外头文件必须映射到对应扩展。编译日志出现头文件缺失时，先补扩展，不要擅自换成另一套陌生库。

使用掌控板兼容目标时，要先区分“软件对象存在”和“星核板实物存在”。`buttonA/buttonB/buzz/accelerometer` 对应 v4.2.2 实物；`display/rgb/light/sound` 需要外接硬件。不得因为积木可见或代码能编译，就报告板载屏幕、RGB、光线或声音输入已可用。

ChatMaker 早期已用 Mind+ 1.8 兼容工具链真实编译七个自研模块示例，结果为 7/7 成功；另外已编译板载按键/蜂鸣器、QMI8658 和该核心 `driver/can.h` 接口的代表性程序。2026-08-25 又用 Mind+ 2 编译板载自检与 OLED 案例。2026-08-26，独立 CLI 用地震预警站完成编译、上传和串口回读。每个 Recipe 保存自己的证据门；Component 卡不继承 Recipe 的上传、串口或实体效果。CAN 编译只证明对应头文件和 P13/P14 配置能生成固件，不证明总线、终端、波特率或协议正确。

星核板板载 CH9102F 支持 USB 串口和自动下载控制，但一个 CH9102F 端口只能作为身份线索，不能单独证明连接的就是星核板。2026-08-25 已在一块用户确认的 v4.2.2 实板上用 Mind+ 2 验证唯一有线端口 COM4、编译、上传、RTS 硬复位和 115200 串口；板载 QMI8658 持续返回数据。蜂鸣器真实发声沿用用户此前确认，OLED 又由用户在 2026-08-26 确认实际成功显示；同一桌面地震预警站中，用户确认 A 键静音和 B 键重新校准均正常。独立 CLI 本轮没有重做这些实体动作。CAN、其余外接模块和断电重启仍保持 `unverified`。调用上传前仍要运行环境检查，并确认唯一合格的有线端口和正确板卡；编译成功不能替代这些验证。

板卡自动识别可以在用户允许时刷入临时识别程序，但这不是普通项目上传：写入前必须完整备份并验证原固件，写入后无论识别成功还是失败都要尝试恢复，恢复验证失败时保留备份并停止后续开发。临时程序的串口报告只提供身份证据，不等于用户项目、模块或实体效果已经运行。
