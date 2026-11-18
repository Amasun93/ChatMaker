---
schema_version: "1.0"
kind: knowledge-page
stable_id: unihiker-m10-start-here
board_id: unihiker-m10
section_id: start-here
source_refs: [source-unihiker-m10-official]
---
# 行空板 M10 从这里开始

行空板 M10 是一台带触屏的小电脑。它在 Debian 上运行 Python，程序可以在电脑上编辑，再传给板子执行。先确认实物是行空板 M10（UNIHIKER M10），再按本页操作。 [M10 官方快速上手](https://www.unihiker.com.cn/wiki/m10/get-started)

1. 先拔掉外设，用一根能传数据的 USB-C 线把板子直接连到电脑。等板子开机，在浏览器打开 `http://10.1.2.3`，看到行空板的管理页就确认了 USB 网络连接。
2. 选一个板上运行的入口。想用浏览器试几行代码，可以从管理页打开板载 Jupyter。想跑完整的 ChatMaker 项目，可以用 Mind+ 的远程连接，或使用老师已经准备好的同步方式。 [板载 Jupyter 教程](https://www.unihiker.com.cn/wiki/m10/jupyter) · [M10 的开发入口](https://www.unihiker.com/wiki/get-started/)
3. 仓库的 `examples/chatduino/unihiker-m10/hello-status/` 是第一个练习。将项目同步到板上，运行 `main.py`，在板上找“ChatMaker 已启动”，在运行终端找 `CHATMAKER_M10_READY`。例程只用板载屏幕，无需外设或 API Key。

ChatMaker 可以先检查源码。课堂记录可以依次勾选“源码检查通过”“项目同步完成”“板上程序启动”“看到实际效果”。打开管理页只确认连接这一步。

[识别与供电](identify-and-safety.md) · [引脚与电气](pins-and-electrical.md) · [同步与运行](toolchains-and-upload.md) · [板载器件与外设](components-and-wiring.md) · [库与例程](libraries-and-examples.md) · [网络与通信](web-and-protocol.md) · [常见问题](troubleshooting.md)
