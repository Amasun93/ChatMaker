---
schema_version: "1.0"
kind: knowledge-page
stable_id: unihiker-m10-toolchains-and-upload
board_id: unihiker-m10
section_id: toolchains-and-upload
source_refs: [source-unihiker-m10-official]
---
# 源码检查、同步和在板上运行

1. **在电脑上检查。** ChatMaker 的 `chatmaker-unihiker` 支持 `check_project`，将 `project` 设为项目目录。它按 Python 3.7 检查入口文件语法、常见不兼容注解和写进代码的凭据，也会提示依赖文件等问题。结果 `source_checked` 可以记为源码预检通过。后续仍需在实物上运行。
2. **传到 M10。** 通过选定的方式同步完整项目目录，包括 `main.py`、依赖清单、示例配置和用到的素材。用 Mind+ 时，核对远程终端已经选中目标板。SSH 是可选路线，向老师取得该板的连接信息与授权。只做浏览器练习时，可通过板载 Jupyter 运行 Notebook。 [M10 开发方式](https://www.unihiker.com/wiki/get-started/) · [Mind+ 与 Jupyter 上手指南](https://www.unihiker.com.cn/wiki/m10/get-started)
3. **确认实际解释器。** Debian 10 的系统 Python 默认是 3.7，ChatMaker 用它做兼容性预检。官方从 0.4.1 系统镜像起提供 pyenv 和额外的 Python 版本。启动项目时，用同一个解释器检查版本和所需库。例如，计划用 `python3 main.py` 就先查 `python3 --version`。从 Jupyter 启动时则检查所选内核。 [官方 Python 版本说明](https://www.unihiker.com/wiki/Troubleshooting/How_to_Install_Multiple_Python_Versions_on_Unihiker/) · [M10 系统更新日志](https://www.unihiker.com.cn/wiki/m10/ReleaseLogs)
4. **先手动运行。** 进到板上的项目目录，用选定的解释器启动 `main.py`，看终端和板载屏幕。需要脱离电脑时，先确认程序能从板上手动打开。连续运行稳定后，再按课堂安排考虑 Home 菜单中的开机自启，重启后另行确认。 [M10 Home 菜单](https://www.unihiker.com.cn/wiki/m10/homemenu)

日常迭代只需更新项目文件，再在板上运行。系统镜像烧录是系统维护操作，可能覆盖板上资料，交给老师备份、核对镜像和处理。 [M10 官方系统镜像说明](https://www.unihiker.com.cn/wiki/m10/burner)
