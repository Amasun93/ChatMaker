# 星核板按钮与调色灯

星核板 v4.2.2 读到外接三线按钮按下时，按旋钮位置输出红、绿、蓝。松开后灯灭。浏览器和真板使用同一份 `light.c` 计算灯色。

| 配套模块 | 接到星核板 |
| --- | --- |
| IDMS-0001 按钮 | VCC → 3V3，GND → GND，SIG → P8 的 S 排 |
| IDMS-0003 电位器 | VCC → 3V3，GND → GND，SIG → P0 的 S 排 |
| IDMD-0001 共阳 RGB 灯 | VCC → 3V3，RED → P9 的 S 排，GREEN → P15 的 S 排，BLUE → P23 的 S 排 |

图中模块端的线序用于示意。接实物时按接口丝印核对。供电用确认过的 3V3 和 GND，可按需要用配套分线件。RGB 按共阳模块使用，每路 PWM 数值越小越亮。

```powershell
chatmaker-sim --demo starcore-rgb-lab --open
chatmaker-hardware --action compile --board-id idmc-0001-starcore-v4-2-2 --sketch examples/chatsim/starcore-rgb-lab
```

开发者修改 `light.c` 后，使用 Zig 0.15.2 重新生成随包程序。

```powershell
zig cc -target wasm32-wasi -mexec-model=reactor -Os -s "-Wl,--export=starcore_light_pwm" examples/chatsim/starcore-rgb-lab/light.c -o runtime/chatmaker/sim_assets/starcore-rgb-lab.wasm
```
