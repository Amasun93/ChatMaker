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

课堂当前路线使用 Mind+ 1.8 的掌控板兼容目标：`dfrobot:mpython:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none`。Mind+ 2.0 的 `mindplus:esp32:mpython:...` 是历史路线，不能混成同一个编译目标。

生成程序前先列出需要添加的 Mind+ 扩展，再给完整 Arduino/C++ 程序。常规程序包含 `MPython.h`；模块额外头文件必须映射到对应扩展。编译日志出现头文件缺失时，先补扩展，不要擅自换成另一套陌生库。

使用掌控板兼容目标时，要先区分“软件对象存在”和“星核板实物存在”。`buttonA/buttonB/buzz/accelerometer` 对应 v4.2.2 实物；`display/rgb/light/sound` 需要外接硬件。不得因为积木可见或代码能编译，就报告板载屏幕、RGB、光线或声音输入已可用。

ChatMaker 已在当前 Mind+ 1.8 工具链中真实编译七个自研模块示例，结果为 7/7 成功；另外已编译板载按键/蜂鸣器、QMI8658 和当前 ESP32 `driver/can.h` 接口的代表性程序。每个 Recipe 保存自己的编译证据 ID、退出码、源码哈希和产物哈希；Component 卡只引用该证据，不重复保存编译明细。CAN 编译只证明当前头文件和 P13/P14 配置能生成固件，不证明总线、终端、波特率或协议正确。

星核板板载 CH9102F 支持 USB 串口和自动下载控制，但一个 CH9102F 端口只能作为身份线索，不能单独证明连接的就是星核板。当前没有实体板，所以没有执行上传。上传、重启、串口输出、CAN 通信和物理效果全部保持 `unverified`。调用上传前仍要先运行环境检查，并确认唯一合格的有线端口和正确板卡；编译成功不能替代这些验证。

板卡自动识别可以在用户允许时刷入临时识别程序，但这不是普通项目上传：写入前必须完整备份并验证原固件，写入后无论识别成功还是失败都要尝试恢复，恢复验证失败时保留备份并停止后续开发。临时程序的串口报告只提供身份证据，不等于用户项目、模块或实体效果已经运行。
