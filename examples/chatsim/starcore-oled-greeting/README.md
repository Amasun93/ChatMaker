# 星核板 A 键和 IDMD-0021 OLED

板型为 IDMC-0001 星核板 v4.2.2。按住板载 A 键显示「你好」，松手显示「再见」。低电平表示按住，A 键已经接在板上的 P5。外接 OLED 通过一条四芯线接同一组 3V3 I²C 接口，使用 P19/SCL、P20/SDA 和地址 0x3C。实物接线看针脚丝印。

```powershell
chatmaker-sim --demo starcore-oled-greeting --open
chatmaker-hardware --action compile --board-id idmc-0001-starcore-v4-2-2 --sketch examples/chatsim/starcore-oled-greeting
```

`greeting.c` 收到 A 键的电平后生成 128×64 单色画面。真板把像素交给 MPython 的 `display.drawImage`，浏览器运行由同一份 C 源码编译的程序并显示这些像素。四个汉字已做成字形点阵。真实 I²C 传输与 OLED 显示在实物上验证。

开发者修改共用程序后，在项目根目录用 Zig 0.15.2 重新生成浏览器程序。

```powershell
zig cc -target wasm32-wasi -mexec-model=reactor -Os -s "-Wl,--export=greeting_update" "-Wl,--export=greeting_pixels" examples/chatsim/starcore-oled-greeting/greeting.c -o runtime/chatmaker/sim_assets/starcore-oled.wasm
```
