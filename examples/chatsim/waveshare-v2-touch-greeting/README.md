# ChatSim · 微雪 V2 触屏问候

适用板卡为微雪 ESP32-S3-Touch-LCD-2.8 V2，屏幕为 240 × 320，触摸芯片为 CST3530。板上的触摸屏就是这个示例的输入和输出。打开预览直接按住屏幕里的「按住我」，看到「你好」，松开恢复「再见」。[微雪板卡资料](https://docs.waveshare.net/ESP32-S3-Touch-LCD-2.8/)

`greeting_ui.c` 是共用的 LVGL 界面。浏览器把指针位置送给 LVGL，并绘制 LVGL 输出的像素。真板通过 ChatMaker 已有的 V2 驱动读取触摸和刷新 LCD。当前预览验证的是触屏界面和程序行为。实板上的触摸与显示以接板后的观察为准。

## 从源码生成浏览器预览

现成示例用 `chatmaker-sim --demo waveshare-v2-touch-greeting --open` 打开。修改界面后，在 ChatMaker 项目根目录运行这条命令重建。开发侧需要 Zig 0.15.2，以及微雪 V2 环境里的 LVGL 8.3.10 库目录。

```powershell
python examples/chatsim/waveshare-v2-touch-greeting/browser/build_preview.py --zig <zig路径> --lvgl <LVGL目录> --output .chatmaker-runtime/previews/chatsim-waveshare-v2-touch.html
```

更新随包示例时，用 `--wasm-output runtime/chatmaker/sim_assets/waveshare-touch.wasm` 生成程序，再从 `chatmaker-sim --demo` 复测。

## 编译微雪 V2 固件

```powershell
chatmaker-hardware --action compile --board-id waveshare-esp32-s3-touch-lcd-2-8 --revision v2 --sketch examples/chatsim/waveshare-v2-touch-greeting
```

两个 C 字体文件来自 ChatMaker CJK Sans 的字形子集。沿用仓库内附的 SIL Open Font License 1.1。生成的 HTML 内嵌 LVGL 的 MIT 许可和字体许可。大小为 62 和 27 像素的字形文件由 `lv_font_conv@1.5.3` 生成，生成参数保留在各文件头部。
