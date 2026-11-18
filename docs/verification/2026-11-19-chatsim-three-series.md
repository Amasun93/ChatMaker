# ChatSim 三系列试用与复测

首批按实物型号选示例。Arduino 和 ESP32 系列里还有其他板型，接入时要补对应板型的测试。

| 系列与具体板型 | 现成示例 | 浏览器实际运行 |
| --- | --- | --- |
| Arduino UNO R3 | `uno-r3-button-led`、`uno-r3-button-oled` | 给 UNO R3 编译的 AVR 固件。浏览器模拟主控、按钮、灯和示例中的 SSD1306 通信。 |
| 微雪 ESP32-S3-Touch-LCD-2.8 V2 | `waveshare-v2-touch-greeting` | 和真板共用的 LVGL 界面。鼠标或手指提供触摸坐标，屏幕显示界面程序画出的像素。 |
| IDMC-0001 星核板 v4.2.2 | `starcore-oled-greeting` | 和真板共用的 A 键输入逻辑及 OLED 像素程序。图上的四芯线已接好，按住 A 显示「你好」，松开回到「再见」。 |

## WorkBuddy 复测提示词

> 先检查你加载的 ChatMaker 源码目录和提交号，把 `chatmaker-sim --version` 的 `source_commit` 和这份复测说明的 GitHub 提交核对。用 `chatmaker-sim --list` 查三类板卡。请打开 `starcore-oled-greeting` 星核板示例，按住图中板载 A 键，然后松手。告诉我屏幕分别显示什么，OLED 四根线接在哪里，以及这次运行的是哪一层仿真。

命令行入口会直接打开随包编译产物。典型课堂试用无需先准备板卡编译环境。

```powershell
chatmaker-sim --list
chatmaker-sim --demo starcore-oled-greeting --open
chatmaker-sim --demo waveshare-v2-touch-greeting --open
chatmaker-sim --demo uno-r3-button-oled --open
```

星核板示例选择 IDMD-0021、`0x3C` 和同一组 3V3 I²C 插口。VCC 对 3V3，GND 对 GND，SCL 对 P19/C，SDA 对 P20/D。A 键已经在板上。针脚位置以实物丝印为准。A 键也参与启动模式选择，接真板后先松开 A 键再上电。[星核板接线](../../knowledge_sources/published/boards/idmc-0001-starcore-v4-2-2/components-and-wiring.md) · [IDMD-0021 元件卡](../../packs/components/idmd-0021-starcore-oled-1-3.yaml)

## 元件目录维护

`--list` 的 `boards` 对应具体板卡与版本，`parts` 关联现有 ChatMaker 元件卡，`demos` 写明每份示例实际用到的器件和运行方式。已有参考资料的元件用 `reference`。加好外观和引脚、接通虚拟行为且有示例复测后，才标 `interactive`。星核板的 B 键、蜂鸣器、QMI8658、三线按钮、电位器、温湿度和超声波目前可查资料。

新增板型时沿用同一个板卡 Wiki 和元件编号。一起提交元件外观和引脚、可运行示例、实际运行层级、默认线路和浏览器复测。批准使用的素材记录来源。能直接跑主控固件时写明仿真器，使用共用界面或业务代码时写明支持的输入和输出。

## 本轮验证

- Windows 上四份随包示例均生成了可独立打开的 HTML。Chromium 离线能复现按下和松开的变化。星核板额外检查了 390 和 320 像素下的触控操作。
- 两份 UNO R3 示例随包文件来自当前源码编译。微雪 V2 的真板示例使用 CST3530 适配环境编译通过，星核板示例使用 ChatMaker 管理的星核板工具链编译通过。示例在真实板上的显示与触摸待观测，WorkBuddy 对话内路由等待按上面的提示词复测。
- 星核板外形参考公开的 [板卡机械资料](../../knowledge/mechanical/boards/idmc-0001-starcore-v4-2-2.json) 与 [OLED 机械资料](../../knowledge/mechanical/components/idmd-0021-starcore-oled-1-3.json)，针脚用接线示意表达。UNO R3 继续使用 [Wokwi Elements](https://github.com/wokwi/wokwi-elements) 和 [AVR8js](https://github.com/wokwi/avr8js)。
