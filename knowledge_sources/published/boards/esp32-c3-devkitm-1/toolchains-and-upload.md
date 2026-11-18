---
schema_version: "1.0"
kind: knowledge-page
stable_id: esp32-c3-devkitm-1-toolchains-and-upload
board_id: esp32-c3-devkitm-1
section_id: toolchains-and-upload
source_refs: [source-esp32-c3-devkitm-1-official]
---
# 编译工具和上传

使用 `chatmaker-hardware`，板卡参数填 `--board-id esp32-c3-devkitm-1`。在 WorkBuddy 中也可以把精确型号和想实现的效果直接告诉 ChatMaker。它按板卡记录准备独立 Arduino 工具。本流程无需启动 Mind+。

1. 首次可用 `prepare-environment --dry-run` 看准备计划，再运行 `prepare-environment`。已有校验通过的组件会复用。用 `doctor` 查看是否准备好。
2. 用 `compile` 检查程序构建。只做这一步时，板子可以留在桌上。
3. 用 `ports` 对比插拔前的串口列表。选本板 Micro-USB 新出现的口，模式用 `uart` 或留默认。确认实物和将写入的程序后，再交给 `run`，指定 `--board-confirmed` 和实际端口。
4. 烧录返回成功后，按草图的波特率打开串口，再观察预期效果并断电重试。分开记录结果。

[乐鑫 USB 转串口和下载模式说明](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32c3/esp32-c3-devkitm-1/user_guide.html)
