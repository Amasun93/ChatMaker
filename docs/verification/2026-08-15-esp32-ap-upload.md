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
- 手机单页：`examples/chatweb/esp32-ap-control.html`
- 固件静态合同测试：`tests/hardware/test_esp32_ap_example.py`
- 页面静态合同测试：`tests/web/test_esp32_ap_page.py`
- WorkBuddy 开发版已经有 `esp32_compile_upload`，只有明确确认载板、排除蓝牙并只剩一个有线端口时才允许继续烧录。
- WorkBuddy 开发版共 23 个工具：2 个资料工具、5 个 Nano 工具、5 个 Uno 工具、5 个 ESP32 工具和 6 个串口工具。

固件的 `GET /` 已内置一份轻量离线控制页，确保不需要联网也能操作。`examples/chatweb/esp32-ap-control.html` 是同一接口合同下的精美手机设计版和本地预览版；目前两者不是同一份页面源码。要把精美版正式烧进开发板，还需要在官方 ESP32 Core 可用后合并并完成真实编译，不能只靠静态复制就算集成成功。

## 手机页面浏览器验收

2026-08-15 使用真实 Chromium 浏览器从 `127.0.0.1` 本地预览打开手机设计版，视口为 `390 × 844`：

- 页面标题为 `DOIT ESP32 AP 控制台`，默认状态为“已断开”。
- 故意读取不存在的本地硬件接口时，页面显示“连接错误 / 状态接口返回 404”，LED 按钮保持不可用。
- 模拟预览明确显示“非真实硬件”，可以读取模拟数据并切换 LED；整个模拟流程为 0 个控制台错误。
- LED 按钮实测为 `118 × 48` 像素，达到手机触控尺寸要求。
- 首次截图发现三块数据卡在两列手机布局中留下一个空色块；修复为最后一块横跨两列后重新截图确认，未保留有缺陷的布局。

这次浏览器验收只证明页面生成和模拟交互，不证明 ESP32、Wi-Fi 或真实 HTTP 已连接。

## 证据边界

| 检查项 | 当前状态 | 能说明什么 |
| --- | --- | --- |
| 固件与页面源文件 | verified | 文件存在，固定引脚、Wi-Fi、页面和接口合同已经写入 |
| 自动合同测试 | verified | 程序结构和页面交互满足当前约定 |
| 手机浏览器模拟交互 | verified | 390 × 844 视口、触控尺寸、断开/错误/模拟状态和 LED 预览已经真实操作；不代表硬件连接 |
| ESP32 官方 Core 3.3.11 | unverified | 本机尚未安装，不能进行真实 ESP32 编译 |
| 固件编译 | unverified | 没有编译成功日志或产物 |
| 固件烧录 | unverified | 没有实物开发板，也没有上传成功记录 |
| 串口启动 | unverified | 没有看到设备真实启动日志 |
| SoftAP 与手机连接 | unverified | 没有手机连入 `ChatMaker-ESP32` 的证据 |
| HTTP 请求与返回 | unverified | 没有设备上的真实往返记录 |
| LED 实体效果 | unverified | 没有确认外接 LED 真的亮灭 |
| 电位器实体读数 | unverified | 没有确认转动后真实数值变化 |
| 断电重启 | unverified | 没有确认重新上电后仍能工作 |

页面里的“模拟预览”只用于看样式和操作感，不能证明 ESP32、Wi-Fi、接口或实体元件已经工作。

## 下一步怎样补齐

1. 先获得用户明确授权，再安装官方 `esp32:esp32@3.3.11` Core。
2. 使用精确 FQBN 真实编译外接 LED 示例和本 AP 案例。
3. 接入已确认身份的 DOIT ESP32 DEVKIT V1，再执行安全烧录。
4. 依次检查串口启动、手机连接、HTTP 往返、LED、电位器和断电重启；每一项单独留证据。

在这些步骤完成前，本案例的准确说法是：**源代码和自动合同已经具备，真实编译与实物全流程尚未验证。**
