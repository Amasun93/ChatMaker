---
schema_version: "1.0"
kind: knowledge-page
stable_id: unihiker-m10-components-and-wiring
board_id: unihiker-m10
section_id: components-and-wiring
source_refs: [source-unihiker-m10-official]
---
# 板载器件和外接设备

| 需要观察的效果 | 从哪里开始 |
| --- | --- |
| 屏上出现文字，或一点就有回应 | 先用板载屏幕做静态显示，按 M10 屏幕的竖屏尺寸排版。文字能显示以后，再试一个触摸按钮。 |
| 用实体按键切换状态 | 用 A、B 验证一次按下对应一次动作。保留 Home 键操作板上菜单。 |
| 读光线或感受板子在动 | 用一个板载传感器和最小读数例子，用手遮住光线传感器或轻轻倾斜板子，观察读数变化。 |
| 提示音或语音播报 | 短提示音用板载蜂鸣器，播放 WAV 或语音用兼容的外接音箱或声卡。录音可从板载麦克风开始。 |
| 摄像头取画面 | M10 的相机应用需要外接摄像头。把兼容的免驱 USB 摄像头接到 M10 的 USB-A，先在板上验证取到一帧。 |

[M10 板载器件与接口](https://www.unihiker.com.cn/wiki/m10/jianjie) · [官方摄像头与音频应用说明](https://www.unihiker.com.cn/wiki/m10/ai_project) · [板载按键与传感器](https://www.unihiker.com.cn/wiki/m10/pinpong_python_lib)

先测一个器件，记下板子和外设的型号以及观察到的结果。接插针模块时先断电，按[引脚与电气](pins-and-electrical.md)核对四件事：接口、方向、信号电平和供电。要装进外壳，先试插头能否插拔、按键能否操作，再固定板子。
