---
schema_version: "1.0"
kind: knowledge-page
stable_id: unihiker-m10-troubleshooting
board_id: unihiker-m10
section_id: troubleshooting
source_refs: [source-unihiker-m10-official]
---
# 行空板 M10 课堂常见问题

## 屏幕有开机画面，电脑却打不开 10.1.2.3？

等板子开机完成，用一根已确认可传数据的 USB-C 线直插电脑，课堂先接一块板。长按 Home 查看网络信息。Windows 检查是否出现可用的 RNDIS 网络适配器，若只看到带警告标志的设备，把设备管理器的情况交给老师或机房管理员处理。若使用 Wi-Fi，请读板子当前地址，教室 Wi-Fi 可能限制设备之间互访。 [官方连接和驱动排查](https://www.unihiker.com.cn/wiki/m10/FAQ) · [官方连接方式](https://www.unihiker.com.cn/wiki/m10/networking)

## 网页能开，为什么没有在板上运行？

先核对当前运行环境。Mind+ 要选中 M10 远程设备，板载 Jupyter 要通过主页的服务开关启动并选内核。从板上的终端运行时，检查项目目录是否已经同步齐全，启动后对照板上屏幕和终端日志。打开 Jupyter 中的 `.py` 文件可以编辑，直接交互运行请使用 Notebook，完整项目也可在板上终端运行。 [Mind+ 快速上手](https://www.unihiker.com.cn/wiki/m10/get-started) · [Jupyter 教程](https://www.unihiker.com.cn/wiki/m10/jupyter)

## 源码检查通过，为什么报找不到库或素材？

在板上查看运行程序的解释器版本。用同一个解释器检查缺的库。确认项目和素材文件夹一起同步了，检查大小写与相对路径。先记录第一条完整报错，再决定要补库、改路径或换课堂准备好的环境。 [M10 Python 环境说明](https://www.unihiker.com/wiki/Troubleshooting/How_to_Install_Multiple_Python_Versions_on_Unihiker/)

## 屏幕、摄像头或语音播报没有反应？

先跑仓库的屏幕问候例程，区分板子能否显示与作品界面本身的问题。如果触摸位置偏移，可以按 Home 菜单的指引校准。摄像头接在 M10 的 USB-A，核对板上的实际设备和是否被前一个程序占用。播报需要可用的外接音频输出，先单独播放一段音频看输出是否正确。 [M10 Home 菜单](https://www.unihiker.com.cn/wiki/m10/homemenu) · [M10 摄像头与音频 FAQ](https://www.unihiker.com.cn/wiki/m10/FAQ)

## 开机就报找不到程序，或者关不掉作品？

在启动它的终端或 IDE 中停掉当前任务，或用 Home 菜单退出从板载菜单启动的程序。若开机提示找不到已删除或移动的脚本，到 Home 菜单关闭开机自启，再手动选择正确项目运行。 [M10 Home 菜单](https://www.unihiker.com.cn/wiki/m10/homemenu)

## 怎样记录课堂验收？

依次记下板型与系统版本、连接方式、Python 版本、源码检查、同步、板端启动、日志、每项外设效果。若作品要独立运行，再观察重启后的实际效果。这批 Wiki 依据官方资料和仓库源码整理，实物效果以本次课堂的板上观察为准。
