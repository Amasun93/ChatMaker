---
schema_version: "1.0"
kind: knowledge-page
stable_id: unihiker-m10-libraries-and-examples
board_id: unihiker-m10
section_id: libraries-and-examples
source_refs: [source-unihiker-m10-official]
---
# 用 Python 库驱动 M10

- **显示和交互。** `unihiker.GUI` 可以显示文字、图片和按钮。仓库的 `examples/chatduino/unihiker-m10/hello-status/` 只要求显示一行文字，可以用来确认基本运行链路。素材放在项目里，路径以程序文件所在目录为起点，避免沿用老师电脑上的绝对路径。 [行空板 unihiker 库](https://www.unihiker.com.cn/wiki/m10/unihiker_python_lib)
- **板载传感器和 IO。** PinPong 通过协处理器读传感器和控制 GPIO。使用每个具体功能前，查官方 M10 例子及它的初始化方式。厂商说明旧版 PinPong 的某些初始化会在固件缺失或不匹配时尝试处理固件，教师可以先核对课堂镜像和库版本。 [PinPong 原理与初始化](https://www.unihiker.com/wiki/LanguageReference/PinPong_Library/pinpong_library_introduction/) · [PinPong 例程索引](https://www.unihiker.com/wiki/LanguageReference/PinPong_Library/)
- **摄像头与声音。** USB 摄像头可用 OpenCV。先确认实际设备、打开状态和读帧结果，退出时释放摄像头，之后再加界面和识别逻辑。播放声音前先选定板上能用的音频输出，作品可用屏幕状态作为提示。 [M10 USB 摄像头示例](https://www.unihiker.com/wiki/LanguageReference/USBDevices/USB_Carema/) · [摄像头与音频应用](https://www.unihiker.com.cn/wiki/m10/ai_project)
- **依赖和凭据。** 用运行项目的那个 Python 检查库能否导入，再决定要补哪些包。有些板上预装了常用库，额外 Python 环境的包另查。离线作品无需 API Key，云服务作品用账号所有者提供的受控凭据或老师提供的代理，示例配置留空。 [官方 Python 版本说明](https://www.unihiker.com/wiki/Troubleshooting/How_to_Install_Multiple_Python_Versions_on_Unihiker/)
