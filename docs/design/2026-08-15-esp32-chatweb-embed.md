# ESP32 ChatWeb 页面嵌入设计

## 目标

让精美手机控制页和 ESP32 固件使用同一份页面源码，避免“本地预览一份、固件里又手改一份”。

## 唯一页面源

```text
可编辑页面源：
examples/chatweb/esp32-ap-control.html

生成后的固件头文件：
examples/chatduino/esp32/ap-led-sensor/page_html.h
```

`page_html.h` 是派生文件，不手工修改。页面有变化时，重新生成它。

## 生成命令

```powershell
chatmaker-web-embed examples/chatweb/esp32-ap-control.html examples/chatduino/esp32/ap-led-sensor/page_html.h --symbol CHATMAKER_AP_PAGE
```

这个命令会：

- 读取 UTF-8 HTML 源文件
- 生成 `PROGMEM` C++ 头文件
- 自动避开 raw string 分隔符冲突
- 生成显式长度常量，方便固件安全发送

## 固件侧约定

- `ap-led-sensor.ino` 只 `#include "page_html.h"`，不再维护第二份页面字符串。
- HTTP `GET /` 使用 `server.send_P(200, PSTR("text/html; charset=utf-8"), CHATMAKER_AP_PAGE, CHATMAKER_AP_PAGE_LENGTH)`。
- 显式长度可以避免构造约 17 KB 的临时 `String`。

## 为什么这样做

1. 浏览器预览和固件页面保持同源，不容易越改越不一致。
2. ChatWeb 只需要维护一份真正可读可改的 HTML。
3. 固件仍然保留离线可访问页面，不依赖外部网络。

## 证据门

| 证据门 | 当前能证明什么 | 还不能证明什么 |
| --- | --- | --- |
| HTML 源文件存在 | 页面设计和交互源码已落地 | 不证明固件已重新嵌入 |
| `chatmaker-web-embed` 生成成功 | 固件头文件来自同一页面源 | 不证明 ESP32 已编译或运行 |
| 浏览器本地预览通过 | 页面布局、按钮、状态切换和模拟交互可用 | 不证明真实硬件已连接 |
| ESP32 固件真实编译通过 | 页面嵌入后的程序能通过精确工具链编译 | 不证明烧录、启动、Wi-Fi 或 HTTP 成功 |
| 实物烧录与启动 | 固件已写入并能开机 | 不证明手机控制与传感器都正常 |
| SoftAP、HTTP、LED、电位器、断电重启 | 各项现场行为分别留证据 | 只有全部通过，才能说案例实机跑通 |

“浏览器模拟正常” 和 “ESP32 实机正常” 不是同一件事，必须分开报告。
