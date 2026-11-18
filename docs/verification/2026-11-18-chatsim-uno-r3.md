# ChatSim · UNO R3 浏览器复测

2026-11-18。ChatSim 用 UNO R3 的实际编译产物运行 AVR 指令。当前课堂电路是一只从 D2 接到 GND 的按钮，程序用 `INPUT_PULLUP` 读取输入，输出是 D13 板载灯。按住时灯亮，松开时灯灭。

## WorkBuddy 复测

打开交付时给出的固定 GitHub 链接，取 `/blob/` 后的 40 位提交号。先更新并重新加载 ChatMaker。核对 `chatmaker-hardware --version` 或 `chatmaker-sim --version` 的 `source_root` 和 `source_commit`。如果刚更新的本地运行环境还没有 `chatmaker-sim`，可以直接用项目的 Python 执行 `-m chatmaker.sim`，也可用同一份源码刷新本地运行入口。

> 我在用 ChatMaker，手边没有 Arduino。先检查你加载的 ChatMaker 源码目录和提交号。请为 UNO R3 写好一个完整程序，D2 接按钮到 GND，按住让 D13 板载灯亮，松开让它灭。然后用 ChatSim 编译你刚保存的这份程序，直接在浏览器打开模拟。告诉我该点哪里，以及编译和仿真分别到了哪一步。

第一次用 Uno R3 时，ChatMaker 会按需准备编译工具，后续复用。浏览器预览是一个自带固件和引擎的 HTML。打开后能看到 UNO R3 和外接按钮。依次点 D2、按钮接点 1，再点 GND、按钮接点 2。两根线接好后用鼠标按住按钮，也可按 Tab 选中，再按住空格。

如果已经在 checkout 里，可用随库的例程复现。

```powershell
chatmaker-sim --sketch examples/chatsim/uno-r3-button-led --open
```

## 验证

Windows 上用实际编译的原版和反转版分别生成 HTML。两份固件在 Chromium 离线环境都按各自的程序响应，390 像素宽也能操作。默认浏览器启动请求成功。WorkBuddy 对话内的加载和调用见上面的复测提示词。

1. 用 ChatMaker 管理的 Arduino 工具编译课堂示例，核对生成的 `.ino.hex` 和预览页显示的固件哈希。
2. 在浏览器先接一根线，按下时灯应保持熄灭。接好第二根线后，按住点亮、松开熄灭。清空接线后再按一次，灯应保持熄灭。
3. 再把实际程序改成「按住熄灭，松开点亮」，重新编译并接线，核对新预览的输出反转。以上验证覆盖固定课堂电路的数字输入输出，真实板子的供电和实物效果需要另行验证。

## 开源引擎

浏览器引擎来自 MIT 许可的 AVR8js 0.21.1。参考其 UNO 示例的处理器、计时器和引脚连接方式。引擎保留原许可，ChatSim 在其上连接 D2 和 D13，并把 ChatMaker 的编译产物封装成网页。用 `npm ci` 后的 `npm run build:chatsim-engine` 可重新生成引擎文件。学生打开生成的页只需浏览器。[AVR8js 项目](https://github.com/wokwi/avr8js) · [上游 UNO 示例](https://github.com/wokwi/avr8js/blob/main/demo/src/execute.ts)

Aily 的公开测试提供了 ESP32-S3 固件经 QEMU 运行的参考。Wokwi 有现成的网页仿真和更多型号的虚拟器件，可以在需要扩大板型时再评估。当前 Demo 的运行路径由 ChatMaker 和 AVR8js 提供。[Aily 仿真测试](https://github.com/ailyProject/aily-blockly/blob/v0.9.113/e2e/electron/fixtures/simulator-live-scenarios.mjs) · [Wokwi 硬件清单](https://docs.wokwi.com/getting-started/supported-hardware)
