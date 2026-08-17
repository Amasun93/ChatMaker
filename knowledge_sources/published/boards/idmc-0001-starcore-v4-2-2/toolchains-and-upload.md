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

ChatMaker 已在当前 Mind+ 1.8 工具链中真实编译七个自研模块示例，结果为 7/7 成功。每个 Recipe 保存自己的编译证据 ID、退出码、源码哈希和产物哈希；Component 卡只引用该证据，不重复保存编译明细。

当前没有实体板，所以没有执行上传。上传、重启、串口输出和物理效果全部保持 `unverified`。调用上传前仍要先运行环境检查，并确认唯一合格的有线端口和正确板卡；编译成功不能替代这些验证。
