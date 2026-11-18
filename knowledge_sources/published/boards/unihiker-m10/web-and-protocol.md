---
schema_version: "1.0"
kind: knowledge-page
stable_id: unihiker-m10-web-and-protocol
board_id: unihiker-m10
section_id: web-and-protocol
source_refs: [source-unihiker-m10-official]
---
# USB 网络、网页和板间通信

**用 USB 数据线直连时**，M10 让电脑看到一张 USB 网卡，Windows 里常叫 RNDIS。官方直连地址是 `10.1.2.3`。一台电脑在课堂上先直连一块 M10。接多块时，先由老师安排能区分每块板的网络配置。无线方式要到板子的 Home 菜单查看当前网络信息，路由器分配的地址可能和 USB 不同。 [官方连接说明](https://www.unihiker.com.cn/wiki/m10/networking) · [DFRobot 多板连接资料](https://wiki.dfrobot.com/dfr0706-en/)

**看网页时**，板子的管理页和 ChatWeb 作品是两个用途。管理页可确认连接、查看和启动已有服务。一个 ChatWeb 页面要读 M10 数据，先确认板上运行什么接口、浏览器从哪里访问，以及网络能否到达该服务。在受信任的课堂网络上调试，Jupyter 或共享服务用完按老师安排关闭。 [M10 本地网页](https://www.unihiker.com.cn/wiki/m10/webmenu)

**让另一块控制板接收命令时**，先画清“谁发送、谁接收、多久等不到就算断开”。约定使用 UART 还是网络、消息格式、超时和断线时输出的安全状态。用 UART 前查实际引脚、信号电平和共地，再用一条能在日志里看到的消息验证两端。 [M10 通信接口参考](https://www.unihiker.com/wiki/LanguageReference/PinPong_Library/)
