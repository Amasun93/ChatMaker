# ESP32 AP 手机控制案例：当前验证记录

## 这个案例要做什么

这个案例的目标很直白：ESP32 自己创建一个 Wi-Fi，手机连上后打开控制页面，可以看电位器数值，也可以打开或关闭一颗外接 LED。它不依赖学校或家庭路由器。

```text
Wi-Fi 名称：ChatMaker-ESP32
页面地址：http://192.168.4.1/
LED：GPIO23
10k 电位器：GPIO34
```

## 开发板身份

本案例只接受下面这一种目标，不会把外形相似的板卡当成它：

```text
载板：DOIT ESP32 DEVKIT V1
模块：ESP-WROOM-32
Profile：doit-esp32-devkit-v1-wroom32
官方 Core：esp32:esp32 3.3.11
FQBN：esp32:esp32:esp32doit-devkit-v1
```

`ESP-WROOM-32` 只是板上的模块名称，不能单独证明整块载板就是 DOIT ESP32 DEVKIT V1。

## 接线说明

接线默认只使用普通文字代码块，便于在本地快速查看和复制。SVG 连线图不是必需步骤；只有用户明确需要图片时才另外生成。

```text
【先拔掉 USB，断电接线】

外接 LED：
1. ESP32 GPIO23 → 330Ω 电阻 → LED 长脚（正极）
2. LED 短脚（负极）→ ESP32 GND

10k 电位器：
3. 电位器一个外侧脚 → ESP32 3V3
4. 电位器中间脚 → ESP32 GPIO34
5. 电位器另一个外侧脚 → ESP32 GND

接好后先检查：
- GPIO34 只能接 3.3V 范围的信号，不能接 5V。
- LED 必须串联 330Ω 电阻。
- 确认无短路后，再插 USB。
```

## 页面和固件怎样共用一份页面源

```text
唯一可编辑页面源：
examples/chatweb/esp32-ap-control.html

生成后的固件头文件：
examples/chatduino/esp32/ap-led-sensor/page_html.h
```

重新生成命令：

```powershell
chatmaker-web-embed examples/chatweb/esp32-ap-control.html examples/chatduino/esp32/ap-led-sensor/page_html.h --symbol CHATMAKER_AP_PAGE
```

固件通过 `#include "page_html.h"` 引入页面，并使用带显式长度的 `send_P` 发送，避免构造约 17 KB 的临时 `String`。

## 页面和设备怎样说话

```text
GET  /
返回手机控制页面

GET  /api/state
返回 LED、电位器和运行时间

POST /api/led
发送 {"on": true} 或 {"on": false}
```

设备状态格式固定为：

```json
{
  "schema_version": "1.0",
  "led_on": true,
  "sensor_raw": 1234,
  "uptime_ms": 56789
}
```

## 已经有的内容

- ESP32 固件：`examples/chatduino/esp32/ap-led-sensor/ap-led-sensor.ino`
- 手机单页唯一页面源：`examples/chatweb/esp32-ap-control.html`
- 生成后的固件头文件：`examples/chatduino/esp32/ap-led-sensor/page_html.h`
- 固件静态合同测试：`tests/hardware/test_esp32_ap_example.py`
- 页面嵌入测试：`tests/web/test_embed.py`
- WorkBuddy 开发版已经有 `esp32_prepare_environment` 和 `esp32_compile_upload`；前者只安装 ChatMaker 验证过的 `esp32:esp32@3.3.11`，后者只有明确确认载板、排除蓝牙并只剩一个有线端口时才允许继续烧录。
- WorkBuddy 开发版共 23 个工具：2 个资料工具、5 个 Nano 工具、5 个 Uno 工具、5 个 ESP32 工具和 6 个串口工具。

## 官方 Core 和真实编译

2026-08-15，本机已经完成下面这些真实结果：

- 官方 `esp32:esp32@3.3.11` 已安装。
- `chatmaker-esp32 {"action":"prepare-environment"}` 返回真实 no-op：
  - `ready_for_compile: true`
  - `fqbn_details_verified: true`
  - `update_performed: false`
  - `installation_performed: false`
- Blink 示例通过 ChatMaker 入口真实编译成功：
  - 程序大小：`271664 bytes`（20%）
  - RAM：`22116 bytes`（6%）
- AP 页面固件通过 ChatMaker 入口真实编译成功：
  - 程序大小：`946528 bytes`（72%）
  - RAM：`47168 bytes`（14%）
  - 依赖库版本：`WiFi` / `Network` / `WebServer` / `FS` / `Hash` 均为 `3.3.11`

这些结果只能证明：官方工具链安装正确、精确 FQBN 正确、当前源码能真实编译。它们不能证明：已经烧录、已经启动、已经建好 AP、手机已经连上、HTTP 已往返成功，或者 LED 与电位器已经真实工作。

## Codex / WorkBuddy 真实刷新

提交进入公开 `main` 并且 GitHub CI 通过后，已执行一次真实的卸载恢复和重新安装：

- Codex 与 WorkBuddy 的 `chatmaker`、`chatduino`、`chatweb` 三个 Skill 文件哈希都与仓库一致。
- WorkBuddy stdio 服务真实启动，版本为 `1.7.0`，`tools/list` 返回 23 个工具。
- `esp32_prepare_environment` 与 `esp32_compile_upload` 确实存在，并保留 HTTP 和实体效果的独立证据门。
- WorkBuddy 配置中原有 5 个非 ChatMaker MCP 全部保留；连同 ChatMaker 入口共 6 个。

安装和进程烟测已经验证，但 Codex 与 WorkBuddy 应用尚未在本轮重启，因此界面是否重新发现新能力仍是 `unverified`。

## 手机页面浏览器验收

2026-08-15 使用真实 Chromium 浏览器从 `127.0.0.1` 本地预览打开手机设计版，视口为 `390 × 844`：

- 页面标题为 `DOIT ESP32 AP 控制台`，默认状态为“已断开”。
- 故意读取不存在的本地硬件接口时，页面显示“连接错误 / 状态接口返回 404”，LED 按钮保持不可用。
- 模拟预览明确显示“非真实硬件”，可以读取模拟数据并切换 LED；整个模拟流程为 0 个控制台错误。
- LED 按钮实测为 `118 × 48` 像素，达到手机触控尺寸要求。

这次浏览器验收只证明页面生成和模拟交互，不证明 ESP32、Wi-Fi 或真实 HTTP 已连接。

## 证据边界

| 检查项 | 当前状态 | 能说明什么 |
| --- | --- | --- |
| 页面源与生成头文件 | verified | 精美页面和固件嵌入页来自同一份 HTML 源 |
| 自动合同测试 | verified | 程序结构、页面交互和嵌入生成满足当前约定 |
| 手机浏览器模拟交互 | verified | 390 × 844 视口、触控尺寸、断开/错误/模拟状态和 LED 预览已经真实操作；不代表硬件连接 |
| 官方 Core 3.3.11 安装 | verified | 本机具备 ChatMaker 锁定的精确官方编译环境 |
| `prepare-environment` 真实 no-op | verified | 机器当前确实已经满足编译前置条件，不是靠文档假设 |
| 固件编译 | verified | Blink 和 AP 固件都已按精确 FQBN 真实编译并生成产物 |
| Codex / WorkBuddy 刷新 | verified | 三个 Skill 哈希一致，WorkBuddy 1.7.0 真实列出 23 个工具并保留 5 个无关 MCP；应用重启后的界面发现除外 |
| 固件烧录 | unverified | 没有实物开发板，也没有上传成功记录 |
| 串口启动 | unverified | 没有看到设备真实启动日志 |
| SoftAP 与手机连接 | unverified | 没有手机连入 `ChatMaker-ESP32` 的证据 |
| HTTP 请求与返回 | unverified | 没有设备上的真实往返记录 |
| LED 实体效果 | unverified | 没有确认外接 LED 真的亮灭 |
| 电位器实体读数 | unverified | 没有确认转动后真实数值变化 |
| 断电重启 | unverified | 没有确认重新上电后仍能工作 |

页面里的“模拟预览”只用于看样式和操作感，不能证明 ESP32、Wi-Fi、接口或实体元件已经工作。

## 下一步怎样补齐

1. 接入已确认身份的 DOIT ESP32 DEVKIT V1。
2. 执行安全烧录，确认上传完成。
3. 依次检查串口启动、手机连接、HTTP 往返、LED、电位器和断电重启；每一项单独留证据。

在这些步骤完成前，本案例的准确说法是：**官方 Core、页面嵌入和真实编译已经具备，真实硬件全流程尚未验证。**
