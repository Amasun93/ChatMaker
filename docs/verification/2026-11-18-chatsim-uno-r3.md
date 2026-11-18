# ChatSim · UNO R3 浏览器复测

2026-11-18。ChatSim 在浏览器运行 UNO R3 的实际编译产物。课堂电路使用一只从 D2 接到 GND 的按钮。可用板载灯观察亮灭，也可用外接 OLED 观察汉字变化。

## WorkBuddy 复测

打开交付时给出的固定 GitHub 链接，取 `/blob/` 后的 40 位提交号。先更新并重新加载 ChatMaker。核对 `chatmaker-hardware --version` 或 `chatmaker-sim --version` 的 `source_root` 和 `source_commit`。如果刚更新的本地运行环境还没有 `chatmaker-sim`，可以直接用项目的 Python 执行 `-m chatmaker.sim`，也可用同一份源码刷新本地运行入口。

> 我在用 ChatMaker，手边没有 Arduino。先检查你加载的 ChatMaker 源码目录和提交号。请为 UNO R3 写好一个完整程序，D2 接按钮到 GND，按住让 D13 板载灯亮，松开让它灭。然后用 ChatSim 编译你刚保存的这份程序，直接在浏览器打开模拟。告诉我该点哪里，以及编译和仿真分别到了哪一步。

第一次用 UNO R3 时，ChatMaker 会按需准备编译工具，后续复用。浏览器预览是一个自带固件、元件图和引擎的 HTML。打开后能看到 UNO R3、外接按钮、已接好的两根线和元件清单。点「运行仿真」，再按住图中的红色按钮。也可按 Tab 选中按钮，再按住空格。

如果已经在 checkout 里，可用随库的例程复现。

```powershell
chatmaker-sim --sketch examples/chatsim/uno-r3-button-led --open
```

## 验证

Windows 上用实际编译的课堂示例生成 HTML，并在 Chromium 离线环境试按按钮。在 1000 和 390 像素宽的窗口中，按钮按下时板载灯亮，松开时熄灭。浏览器自动测试也检查了相反输出的 AVR 程序和 320 像素宽的界面。WorkBuddy 对话内的加载和调用见上面的复测提示词。

1. 用 ChatMaker 管理的 Arduino 工具编译课堂示例，核对生成的 `.ino.hex` 和预览页显示的固件哈希。
2. 打开网页，核对蓝线从 D2 接到按钮左上脚，深灰线从电源排针 GND 接到按钮左下脚。点「运行仿真」，按住按钮看板上的灯和状态提示一起点亮，松开后一起熄灭。
3. 可把实际程序改成「按住熄灭，松开点亮」，重新编译后核对输出反转。以上验证覆盖这条课堂电路的数字输入输出。真实板子的供电和实物效果需要另行验证。

## UNO R3 按钮和 OLED

> 先检查你加载的 ChatMaker 源码目录和提交号。用 ChatSim 编译随库的 `uno-r3-button-oled` 示例，选择 `button-oled` 电路，直接打开浏览器。我要看到 UNO R3、外接按钮、SSD1306 小屏幕和已经接好的六根线。启动时显示「再见」，按住按钮显示「你好」，松手变回「再见」。分别告诉我编译结果和网页里观察到的结果。

```powershell
chatmaker-sim --sketch examples/chatsim/uno-r3-button-oled --circuit button-oled --open
```

仿真里的 SSD1306 为 128×64，地址是 `0x3C`。屏幕的 SDA 接 A4，SCL 接 A5，另有 5V 和 GND。接实物时选标明支持 5V 供电及 I²C 信号的模块，按丝印对照针脚。示例用 Arduino 自带的 `Wire` 库和固件内画好的四个汉字。[Arduino I²C 引脚](https://docs.arduino.cc/learn/communication/wire/#arduino-i2c-pins) · [SSD1306 元件资料](https://docs.wokwi.com/parts/board-ssd1306)

Windows 上实编译并在 Chromium 离线打开，核对了 1120 像素下的鼠标和 390 像素下的触控。启动、按住、松手、停止、重启时的屏幕像素与预期相符。实板显示和 WorkBuddy 对话加载需要各自复测。

## 开源引擎

浏览器引擎来自 MIT 许可的 AVR8js 0.21.1。参考其 UNO 示例的处理器、计时器和引脚连接方式。引擎保留原许可，ChatSim 在其上连接 D2 和 D13，并把 ChatMaker 的编译产物封装成网页。用 `npm ci` 后的 `npm run build:chatsim-engine` 可重新生成引擎文件。学生打开生成的页只需浏览器。[AVR8js 项目](https://github.com/wokwi/avr8js) · [上游 UNO 示例](https://github.com/wokwi/avr8js/blob/main/demo/src/execute.ts)

板卡和按钮来自 MIT 许可的 Wokwi Elements 1.9.2。ChatSim 使用元件自带的针脚坐标画线，并把按钮状态和 D13 灯连接到 AVR8js。生成的页面保留元件和依赖的许可证。[Wokwi Elements](https://github.com/wokwi/wokwi-elements)

Aily 的公开测试提供了 ESP32-S3 固件经 QEMU 运行的参考。Wokwi 有现成的网页仿真和更多型号的虚拟器件，可以在需要扩大板型时再评估。当前 Demo 的运行路径由 ChatMaker 和 AVR8js 提供。[Aily 仿真测试](https://github.com/ailyProject/aily-blockly/blob/v0.9.113/e2e/electron/fixtures/simulator-live-scenarios.mjs) · [Wokwi 硬件清单](https://docs.wokwi.com/getting-started/supported-hardware)
