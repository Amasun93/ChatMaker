# 微雪 V2 平衡球反馈与复测

[Issue #6](https://github.com/Amasun93/ChatMaker/issues/6) 对应微雪 ESP32-S3-Touch-LCD-2.8 V2 / CST3530。此前随包验证的是屏幕和触摸示例。平衡球同时用到 QMI8658、连续绘制、原生 USB 及碰撞音频，每个环节都需要自己的证据。

## 已有证据和边界

| 项目 | 已观察到的事实 | 证据范围 |
| --- | --- | --- |
| Windows GCC | 在同一份 14.2.0 编译器和同一份头文件上，用含空格的 123 字符编译器根路径复现 `bits/error_constants.h` 缺失。改为显式的标准库和 `xtensa-esp-elf/esp32s3/no-rtti` 绝对路径后，`#include <system_error>` 检查通过。 | 可复现的是路径触发的头文件搜索失败。Issue 当时的完整环境和更深路径仍需按实际机器检查。归档和文件原地保留。 |
| 编译超时 | Issue 报告首次编译达到 900 秒上限，而且缓存复用后才看到首条头文件错误。工具现在可复用固定目录、设超时和指定并发数。 | 900 秒只说明当次到达时间上限。是否仍在编译可对照对象文件的写入和 CPU 活动。 |
| USB CDC | Issue 中主机持续读时流畅，裸玩时周期日志与约 161 ms 间隔伴随出现。移除热路径周期写入、改为按指令导出后，报告的卡顿消失。 | 硬件 CDC 写入会等发送缓冲腾出空间。`isConnected()` 只说明连接判断，较短的单次写等待仍可被内部重试放大。新样例实板手感需单独验证。[Arduino-ESP32 3.3.11 的 HWCDC 实现](https://github.com/espressif/arduino-esp32/blob/3.3.11/cores/esp32/HWCDC.cpp) |
| 残影 | v6.4 报告整块 240×246 游戏区在内存合成后一次提交，用户确认无残影。 | 局部擦除的底层失效原因仍未定位。网格、相位和先擦后画出现过问题，单凭持续轨迹也不能归因于 tearing。新倾斜小球样例同样使用完整区域，区域大小为 240×192。 |
| 音效 | Issue 的 v7 编译并写入。四秒测试后报告没有记录到大于 30 ms 的帧间隔。 | 实际发声、I²S 初始化、视觉特效与操作手感由 v7 的后续实物复测确认。工具提供 `ESP_I2S` API，未宣称原厂音频与 SD 例程已整体配齐。 |

## WorkBuddy 复测

> 先用 `chatmaker-hardware --version` 确认源码目录和我给出的 GitHub 完整提交。按微雪 ESP32-S3-Touch-LCD-2.8 **V2 / CST3530** 诊断，告诉我 `peripheral_coverage` 和本机编译准备状态。用同一专用构建目录把 V2 倾斜小球编译两次，报告当前编译的时间和产物。遇到超时保留第一条错误和实际进度。确认真板及端口后再烧录。实际观察屏幕和倾斜输入，先在串口助手关闭时玩一段，再连接串口发送 `D`。请把编译结果、诊断读数和看到的效果分别报告。

```powershell
$board = "waveshare-esp32-s3-touch-lcd-2-8"
chatmaker-hardware --action doctor --board-id $board --revision v2
chatmaker-hardware --action prepare-environment --board-id $board --revision v2
chatmaker-hardware --action compile --board-id $board --revision v2 `
  --sketch examples/chatduino/waveshare-s3/v2-tilt-dot `
  --build-path .chatmaker-runtime/builds/waveshare-v2-tilt-dot --compile-timeout 1800 --jobs 2
```

第一次选择新的或空的构建目录。之后为同一草图和版本复用目录。浏览 `compile.build_path` 可定位对象文件，实际烧录使用本次独立导出的 `compile.artifact_dir`。普通编译仍接受原来的调用方式。屏幕与计时器的串口查询用 `?`，小球的诊断用 `D`。

本机 Windows 使用缓存中的 Arduino CLI 1.3.1 回退版、Arduino-ESP32 3.3.11 和 GCC 14.2.0。V2 小球冷编译用时约 392 秒，同一目录修改后复编约 43 秒。两次导出位于不同目录，程序二进制的哈希也随源码变化。另以 1 秒上限验证了 `compile_timeout`、诊断文本和进程树退出。时间仅为本机记录。小球新示例的烧录、屏幕效果、倾斜方向和手感待实物观察。

## GitHub 自动测试

- [最近的 Windows CI](https://github.com/Amasun93/ChatMaker/actions/runs/44354493925) 通过。[macOS 最近一次运行](https://github.com/Amasun93/ChatMaker/actions/runs/44354493733) 的 Apple 芯片任务通过。Intel 任务在 40 分钟上限附近取消，下载的结果显示直到 C3 仍成功，已完成 C6 准备，C6 编译结果文件为空。
- [另一轮 macOS 失败](https://github.com/Amasun93/ChatMaker/actions/runs/44334841906) 在 K10 下载时重试多次，并出现 GitHub 产物上传 DNS 错误。
- 新流程给 Intel 和 Apple 芯片分别运行微雪及其他板型测试。原有样例继续编译。微雪组新增 V2 小球；其他板组保存校验过的 K10 官方压缩包。网络类下载错误会重试，结果上传失败会再尝试一次。
