# ChatSim 1.0.1 Arduino 与 ESP32 基础元件

```powershell
chatmaker-sim --version
chatmaker-sim --library arduino --open
chatmaker-sim --library esp32 --open
chatmaker-sim --library starcore --open
```

Arduino 和 ESP32 共用十种基础素材，分别按自己的实验标注使用情况。包括按钮、直插 LED、330 Ω 电阻、10 kΩ 电位器、四针 I²C OLED、SG90 舵机、HC-SR04、DHT22、光敏模块和无源蜂鸣器。「可互动」可在该板的课堂实验中试；「接线用」画进线路帮助接实物；其余卡片供认元件、查引脚和接线注意事项。

## 两块板做同一个实验

| 主控 | 旋钮两端 | 旋钮中间脚 | LED 接线 | 浏览器运行内容 |
| --- | --- | --- | --- | --- |
| Arduino UNO R3 | 5V 和 GND | A0 | D3 → 330 Ω 电阻 → 红色 LED 长脚，短脚接 GND | UNO R3 编译固件，模拟读取 A0 和 D3 上的脉冲 |
| DOIT ESP32 DEVKIT V1 30 针版 | 3V3 和 GND | GPIO34 | GPIO18 → 330 Ω 电阻 → 红色 LED 长脚，短脚接 GND | 和真板共用的调光程序，接收虚拟旋钮输入 |

转图中的旋钮或拖动下方滑条，LED 从灭到亮。显示的百分比对应输出脉冲的占比，用来观察程序变化。换到真板时按实物丝印和上表接线。ESP32 图中的 DOIT 针脚适用于 30 针版，微雪 V2 的板载触屏实验在同一库的另一入口。

UNO R3 也可使用自己的草图。选用 A0 读旋钮，D3 输出 PWM。编译后用固定的虚拟线路试运行。

```powershell
chatmaker-sim --sketch <UNO草图目录> --circuit knob-led --open
```

## WorkBuddy 复测

> 先运行 `chatmaker-sim --version`，告诉我你实际加载的源码路径、`runtime.source_commit` 和 `chatsim_version`。对照我给你的 GitHub 完整提交号，确认版本为 `1.0.1`。打开 Arduino 和 ESP32 两套元件库，分别找到「转旋钮调 LED 亮度」，转到起点、中间、终点。告诉我你看到的变化，两块板的旋钮和 LED 各用哪些针脚，以及各自实际运行的程序。最后去 ESP32 库打开微雪 V2，复测板载屏幕按钮。

Windows Chromium 已离线验证两套库、实体图中的旋钮和滑条输入、灯灭到全亮、四针 OLED 插口图、390 像素页面，以及旧的微雪、UNO R3、星核实验。UNO R3 与 DOIT 的真板程序均由 ChatMaker 独立工具链编译通过。真板上的实际接线和灯效待实物复测。

## 素材来源与增补

- UNO R3 使用 [AVR8js](https://github.com/wokwi/avr8js) 模拟主控。两块板和常见元件的外观使用 [Wokwi Elements](https://github.com/wokwi/wokwi-elements)，随包保留依赖的许可文字。四针 OLED 的外观和串联的接线图来自 ChatSim。微雪 V2 使用和固件共用的 [LVGL](https://github.com/lvgl/lvgl) 界面。
- 星核板上轮的 11 项「外形与孔位」各有机械卡，其中 7 项有已列出的引脚名。星核专用模块的详图需要能和型号对应的资料。通用模块的图可以帮助认类型，星核专用接口按自身元件卡维护。有已接好的实验并验证过输入输出后，再把该模块标为可互动。
- 修改第三方图形或 AVR 模拟依赖后，在源码仓库执行 `npm run build:chatsim-engine`。UNO 的随包 HEX 来自 [对应草图](../../examples/chatsim/uno-r3-knob-led/uno-r3-knob-led.ino) 的干净编译。DOIT 预编译程序由 [共享调光源码](../../examples/chatsim/esp32-devkit-knob-led/knob.c) 生成。

```powershell
zig cc -target wasm32-wasi -mexec-model=reactor -Os -s "-Wl,--export=knob_pwm" examples/chatsim/esp32-devkit-knob-led/knob.c -o runtime/chatmaker/sim_assets/esp32-devkit-knob-led.wasm
```
