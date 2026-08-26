# micro:bit V2 虚拟下载链验证

日期：2026-08-26

## 范围

- 目标：在没有 micro:bit 实板时，验证固定环境、代表源码、HEX 打包、目标盘身份判断和 `FAIL.TXT` 错误处理。
- 不包含：真实 DAPLink 写入、重新枚举、115200 CDC 串口、断电重启、LED或按键实体效果。

## 固定环境

- MicroPython V2：2.1.1，1,239,726 字节，SHA-256 `5bd5d4584a5caae740a66d38f93651968569dd4b52f4bc132ebf3c6fdf3847ac`。
- `@microbit/microbit-fs`：0.10.0，npm integrity `sha512-n6DEVqqaQAL/EDLyXh+1nsdRV16ePFqROeFeNlOoTS23eB8zF8qhA+IaNHRT07sy0zgCGg3YCZgP+zcCIRzP6A==`。
- 安装：隔离目录执行 `npm ci --ignore-scripts --no-audit --no-fund`，退出码 0；锁文件同时固定 `microbit-universal-hex 0.2.2`、`nrf-intel-hex 1.4.0` 和 `tslib 2.8.1`。

## 代表案例

- 源码：`examples/chatduino/microbit-v2/heart-status/main.py`
- 源码检查：通过；92 字节；SHA-256 `e3b6275aa9871b38c2edf688daebfc625ccec94bfb5706734dd86dae06923c67`。
- HEX 打包：退出码 0；输出 1,240,048 字节；SHA-256 `ca4b7459fe2ac72956aeb90ed774ba867d10c7a0d9f290015f4c1e06e3c52984`。
- 反向校验：从输出 HEX 读取到的 `main.py` 与输入源码逐字节一致。
- 证据名称：这是 `source_checked` 和 `hex_packaged`，不是原生 `code_compiled`。

## 虚拟盘证据

聚焦测试使用临时目录模拟 DAPLink 卷：

- 只有卷标为 `MICROBIT`、存在 `DETAILS.TXT` 且接口版本不低于 0255 时，才识别为 V2 上传目标。
- 普通 U 盘卷标、`MAINTENANCE`、缺少 `DETAILS.TXT` 和 V1 0249 接口均被拒绝。
- 多个匹配目标时要求显式选择。
- HEX 写入、`FAIL.TXT`、重新枚举、串口和实体效果分别记录；模拟写入不会升级后三项状态。

## 当前最高证据门

环境准备、源码检查和 HEX 打包已真实验证。虚拟目标选择和失败提示已通过测试。由于没有实板，真实 DAPLink 写入及其后的所有硬件门仍为 `unverified`。
