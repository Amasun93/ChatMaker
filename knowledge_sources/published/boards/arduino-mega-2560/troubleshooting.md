---
schema_version: "1.0"
kind: knowledge-page
stable_id: arduino-mega-2560-troubleshooting
board_id: arduino-mega-2560
section_id: troubleshooting
source_refs: [source-arduino-mega-2560-official]
---
# 课堂常见问题与验收

| 看到的现象 | 现在做什么 | 看到什么可以继续 |
| --- | --- | --- |
| 每次开始都在准备工具 | 在同一个环境运行 `doctor`，用 `prepare-environment --dry-run` 看本次缺件，确认是否换了工具目录、依赖库或板卡 | `ready_for_compile: true` 时开始编译。所需组件都已安装或归档已备齐时，准备计划显示剩余下载为 0 |
| 电源灯亮，端口列表没有 Mega | 换能传数据的 USB 线，直接插电脑，拔插比较端口列表。兼容板若仍没端口，查板商标注的 USB 转串口芯片和驱动 | 新端口随本板拔插消失、出现 |
| 工具列表里有多个 Mega 选项 | 对照主芯片标记选 ATmega2560。再用拔插确认本次连接的端口 | 编译目标对应 ATmega2560，写入前选中了实物端口 |
| 出现缺头文件或找不到库 | 先找到第一条报错对应的头文件，核对库名、版本和 AVR 支持，准备对应库后，用同一份程序重编译 | 缺库错误消失，生成 `.hex` |
| 编译成功，写入报端口占用或 `avrdude` 超时 | 关掉串口监视器和占端口的网页。断电后移除 `RX0`、`TX0` 的接线和扩展板，重新接 USB。再核对主芯片和端口重试 | 工具报告写入成功，板子能运行写入的程序 |
| 工具说写入成功，灯没按要求闪 | 观察标着 `L` 的灯。拔掉外设，确认 Blink 用 `LED_BUILTIN`，把亮灭间隔调到容易观察再写入 | `L` 灯连续几轮按设定节奏亮灭 |
| 串口是空白或乱码 | 选当前 Mega 的端口，把监视器波特率设成程序值。为测试改成定时打印固定文字，留几秒等板子启动 | 监视器稳定读到完整的测试文字 |

保存板型、所选端口和第一条关键报错。资料核对、编译、写入、串口运行和灯或模块效果都有各自的验收结果。需要验收上电自启时，先安全断开供电，再重新通电，检查程序是否从预期状态开始。

[Arduino 官方找不到端口排错](https://support.arduino.cc/hc/en-us/articles/4412955149586-If-your-board-is-not-detected-by-Arduino-IDE) · [Arduino 官方写入排错](https://support.arduino.cc/hc/en-us/articles/4403365313810-If-your-sketch-doesn-t-upload)
