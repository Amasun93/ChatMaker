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

Mind+ 1.8 和 2 都是已验证支持的后端，优先复用电脑里已有的可用版本；两者都有时当前适配器默认选择 2，这不表示 1.8 不够用。板载自检与 IDMD-0021 OLED 案例都已在 COM4 完成编译、上传、RTS 硬复位和 115200 串口验证。

证据按对象继续分开：QMI8658 有传感数据；蜂鸣器真实发声沿用用户此前确认；A/B 键只读到空闲状态，没有按下/松开观察；OLED 先取得 `STARCORE_OLED_READY` 代理标记，随后用户又确认屏幕实际成功显示。后续画面优先使用简洁中文，并避免在循环中反复清空整屏造成闪烁。

权威状态读取 `packs/boards/idmc-0001-starcore-v4-2-2.yaml`、`packs/recipes/starcore-onboard-self-test.yaml` 和 `packs/recipes/starcore-idmd-0021-oled-message.yaml`；本段由 `scripts/sync_starcore_evidence.py` 生成。
<!-- starcore-evidence-summary:end -->

Mind+ 1.8 和 2 都是已验证支持的星核板后端，优先复用电脑里已有的可用版本，不要求为了版本偏好再安装另一套。两者都可用时，当前适配器为保持选择稳定会默认使用 2；这不表示 1.8 不够用。Mind+ 2 目标为 `mindplus:esp32:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none`，Mind+ 1.8 目标为 `dfrobot:mpython:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none`，不能混用路径和上传参数。两者都没有时才推荐已验证的 1.8.x 下载。

生成程序前先列出需要添加的 Mind+ 扩展，再给完整 Arduino/C++ 程序。常规程序包含 `MPython.h`；模块额外头文件必须映射到对应扩展。编译日志出现头文件缺失时，先补扩展，不要擅自换成另一套陌生库。

使用掌控板兼容目标时，要先区分“软件对象存在”和“星核板实物存在”。`buttonA/buttonB/buzz/accelerometer` 对应 v4.2.2 实物；`display/rgb/light/sound` 需要外接硬件。不得因为积木可见或代码能编译，就报告板载屏幕、RGB、光线或声音输入已可用。

ChatMaker 早期已用 Mind+ 1.8 回退工具链真实编译七个自研模块示例，结果为 7/7 成功；另外已编译板载按键/蜂鸣器、QMI8658 和该核心 `driver/can.h` 接口的代表性程序。2026-08-25 又用优先的 Mind+ 2 编译板载自检与 OLED 案例。每个 Recipe 保存自己的证据门；Component 卡不继承 Recipe 的上传、串口或实体效果。CAN 编译只证明对应头文件和 P13/P14 配置能生成固件，不证明总线、终端、波特率或协议正确。

星核板板载 CH9102F 支持 USB 串口和自动下载控制，但一个 CH9102F 端口只能作为身份线索，不能单独证明连接的就是星核板。2026-08-25 已在一块用户确认的 v4.2.2 实板上用 Mind+ 2 验证唯一有线端口 COM4、编译、上传、RTS 硬复位和 115200 串口；板载 QMI8658 持续返回数据。蜂鸣器真实发声沿用用户此前确认，OLED 又由用户在 2026-08-26 确认实际成功显示。按键动作、CAN、其余外接模块和断电重启仍保持 `unverified`。调用上传前仍要运行环境检查，并确认唯一合格的有线端口和正确板卡；编译成功不能替代这些验证。

板卡自动识别可以在用户允许时刷入临时识别程序，但这不是普通项目上传：写入前必须完整备份并验证原固件，写入后无论识别成功还是失败都要尝试恢复，恢复验证失败时保留备份并停止后续开发。临时程序的串口报告只提供身份证据，不等于用户项目、模块或实体效果已经运行。
