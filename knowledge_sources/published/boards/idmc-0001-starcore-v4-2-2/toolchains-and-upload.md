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

ChatMaker 当前只把星核板工具链知识标记为来源已核对，没有在本仓库重新完成编译或上传。调用编译前先运行环境检查；只有真实编译返回成功才能写“已编译”。上传还需要唯一合格的有线端口和板卡确认；上传成功也不能替代重启、串口或实体效果验证。
