---
schema_version: "1.0"
kind: knowledge-page
stable_id: mpython-v3-libraries-and-examples
board_id: mpython-v3
section_id: libraries-and-examples
source_refs: [source-mpython-v3-official]
---
# 彩屏对象是 display

3.0 的 MicroPython 显示对象是 `display`，采用 320×172 RGB565；不要复制经典版 `oled` 的单色 128×64 坐标和 API。`light.read()` 返回 lux，和经典版 0–4095 的模拟原始值不同；`sound.read()` 仍按官方示例处理为 0–4095。

加速度、陀螺仪、磁力计、按键、触摸和 RGB 的高层名称与经典生态有相似处，但相似名称不代表底层引脚、驱动和固件相同。

