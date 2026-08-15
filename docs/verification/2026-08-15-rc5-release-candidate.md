# ChatMaker v0.1.0-rc5 本地发布候选验证

## 状态与范围

- Python 包版本：`0.1.0rc5`
- 发布目录名：`ChatMaker-0.1.0-rc5`
- 状态：本地候选；未推送、未打标签、未创建 GitHub prerelease、未上传资产，也没有 GitHub CI 的 rc5 提交结果。
- rc1、rc2、rc3、rc4 的发布物和历史验证记录保持不变。

rc5 收录 Nano/Uno 的 Mind+ 工作流、锁定官方 Core/FQBN 的 ESP32 工作流、ESP32 AP 内嵌页面、可执行路由、创意简报规划、显式高级游乐场、WorkBuddy 1.7.0 的 23 个工具，以及 Chromium 自动化。

## 工作树软件验证

2026-08-15 在 Windows 64 位、Python 3.11 环境运行：

```powershell
python -m unittest discover -s tests -v
python runtime/doctor.py
python scripts/validate_skills.py
python -m unittest discover -s tests\release -p "test_release_package.py" -v
npm run test:browser
git diff --check
```

结果：

- 单元/集成/发布合同测试：`Ran 189 tests ... OK`。
- doctor：3 块板卡、12 个元器件、14 个配方，三套 Skill 均 `ok: true`。
- 独立 Skill 校验：`chatmaker`、`chatduino`、`chatweb` 均 `[OK]`。
- 发布合同聚焦运行：`Ran 7 tests ... OK`；覆盖 rc5 默认版本、确定性构建、ESP32/路由/网页/浏览器/安装资产清单、ESP32 运行期缓存排除、先校验后解压顺序、WorkBuddy stdio 帮助边界，以及 AP 超时修正的先后顺序。
- Playwright Chromium：`4 passed`；覆盖课堂页、模拟硬件页、ESP32 AP 模拟页和高级游乐场。
- `git diff --check`：退出码 0；只显示 Windows LF/CRLF 工作区转换提醒，无空白错误。

## 确定性构建与全新解压

最终发布 ZIP 从同一提交源连续构建两次，两份 ZIP 必须字节相同，SHA-256 必须一致。最终哈希保存在 ZIP 同目录的 `.sha256` 文件和任务报告中，不写回本文件，避免“把哈希写进 ZIP 后改变 ZIP 自身”的循环。

全新解压验证必须满足：

- 解压到新的临时目录；使用新的 Python venv。
- 清除 `PYTHONPATH`，从解压目录执行 editable install，并确认 `chatmaker.__file__` 位于解压目录而不是工作树。
- 从解压源码运行 doctor、三套 Skill 校验和 WorkBuddy stdio `initialize` / `tools/list`。
- WorkBuddy 必须报告版本 `1.7.0` 和 23 个工具。
- Nano Blink、Uno Blink、ESP32 Blink 和 ESP32 AP 固件只执行编译；不得调用上传。
- 在解压目录执行 `npm ci` 和真实 Chromium 浏览器测试。

## ESP32 AP 超时诊断与修正

文档修订后的第一次 AP 全新解压编译在 900 秒默认预算下超时。该次运行没有返回成功，也没有生成可作为成功证据的 application `.ino.bin`；因此不能写成 AP 编译通过。

诊断比较了成功样本与超时样本：AP 源码、生成头文件、官方 Core `esp32:esp32@3.3.11`、精确 FQBN `esp32:esp32:esp32doit-devkit-v1`、Arduino CLI、构建卷、缓存预热顺序均相同。超时前编译器仍在推进预处理输出，stderr 只有 `TimeoutExpired`，没有编译器诊断。证据支持固定 900 秒预算在瞬时主机吞吐下降时过脆，而不支持源码、Core、FQBN 或路径差异是根因。

随后将 ESP32 编译默认预算修正为 1200 秒；显式请求 `timeout` 仍可覆盖默认值。上传预算没有改变，`upload_timeout` 仍为 300 秒。Nano、Uno 和所有上传路径均未改动。

## 修正后候选的首次成功全新解压复验

修正后的候选从新归档解压到新的临时目录，venv 位于解压源码外；`PYTHONPATH` 已清除。本文不保存临时 GUID 路径，最终 ZIP 路径和 SHA-256 只写入同目录 sidecar 与忽略的 Task 4 报告，避免自引用改变归档字节。

最终结果：

- 安装元数据版本为 `0.1.0rc5`；`chatmaker.__file__` 位于本次新解压源码的 `runtime\chatmaker\__init__.py`，不是工作树路径。
- doctor 为 3 块板卡 / 12 个元器件 / 14 个配方，三套 Skill 均通过；独立 Skill 校验全部 `[OK]`。
- 发布合同聚焦运行 5/5 通过。
- WorkBuddy stdio `initialize` 返回 `serverInfo.version = 1.7.0`，`tools/list` 返回 23 个工具。
- Nano Blink compile-only：`mindplus:avr:nano:cpu=atmega328`，程序 2002 B、RAM 204 B，成功。
- Uno Blink compile-only：`mindplus:avr:uno`，程序 2008 B、RAM 204 B，成功。
- ESP32 Blink compile-only：官方 Core 3.3.11 与精确 DOIT FQBN，程序 271664 B、RAM 22116 B，成功。
- ESP32 AP compile-only：省略请求 `timeout`，使用修正后的 1200 秒默认预算；1056.41 秒成功，程序 946528 B、RAM 47168 B。官方 Core 为 3.3.11，FQBN 为 `esp32:esp32:esp32doit-devkit-v1`；WiFi、Networking、WebServer、FS、Hash 均为 3.3.11。
- 解压源码 `npm ci` 成功，安装 3 个包、0 个漏洞；Chromium 自动化 4/4 通过。
- 所有硬件命令都只使用 `action: compile`；没有调用 `compile-upload` 或 `upload`，也没有串口、网络连接、断电重启或物理效果操作。

## 最新最终归档的全新解压复验

修订验证时间线并重新构建归档后，又从新的临时目录和新的外部 venv 完成了一次全套复验。安装、doctor、Skill、发布合同、WorkBuddy、Nano/Uno 编译和 Chromium 结果与上节一致；ESP32 的本次精确结果为：

- ESP32 Blink compile-only：省略请求 `timeout`，220.876 秒成功，程序 271664 B、RAM 22116 B。
- ESP32 AP compile-only：省略请求 `timeout`，使用 1200 秒默认预算；904.292 秒成功，程序 946528 B、RAM 47168 B。官方 Core 为 3.3.11，FQBN 为 `esp32:esp32:esp32doit-devkit-v1`；WiFi、Networking、WebServer、FS、Hash 均为 3.3.11。
- Chromium 自动化 4/4 通过；整个复验仍然没有调用 `compile-upload`、`upload`、串口、网络连接、断电重启或物理效果操作。

## 证据门

| 检查项 | rc5 状态 | 证据边界 |
| --- | --- | --- |
| 包安装和 Python import | verified | 只证明解压源码可安装、import 来自解压目录 |
| doctor 与 Skill 校验 | verified | 只证明包记录和 Skill 合同有效 |
| WorkBuddy stdio | verified | 只证明服务进程返回 `1.7.0` 和 23 个工具；不证明 WorkBuddy UI 重启后已发现 |
| Nano Blink 编译 | verified | 只证明 Mind+ 后端可把解压源码编译为 AVR 产物 |
| Uno Blink 编译 | verified | 只证明 Mind+ 后端可把解压源码编译为 AVR 产物 |
| ESP32 Blink / AP 编译 | verified | 只证明官方 Core 3.3.11 和精确 DOIT FQBN 可生成 ESP32 二进制 |
| 四个网页的 Chromium 自动化 | verified | 只证明本地浏览器布局和交互；ESP32 页运行的是明确标注的模拟模式 |
| Nano 固件上传 | unverified | 没有有线 Nano 上传成功证据 |
| Nano 启动串口、断电重启、板载灯和外接模块效果 | unverified | 编译结果不能替代任何一项实物证据 |
| Uno 固件上传 | unverified | 没有有线 Uno 上传成功证据 |
| Uno 启动串口、断电重启和板载灯效果 | unverified | 编译结果不能替代任何一项实物证据 |
| ESP32 固件上传 | unverified | 没有已确认身份的有线 DOIT ESP32 DevKit V1 上传记录 |
| ESP32 启动串口 | unverified | 没有真实启动日志 |
| ESP32 SoftAP 与手机连接 | unverified | 浏览器模拟不证明 `ChatMaker-ESP32` 已建立或手机已接入 |
| ESP32 真实 HTTP 往返 | unverified | 没有开发板上的 `GET /api/state` 或 `POST /api/led` 往返证据 |
| ESP32 LED、电位器和断电重启 | unverified | 没有物理亮灭、真实 ADC 变化或重新上电恢复证据 |
| Codex / WorkBuddy 应用界面发现 | unverified | stdio 和安装器检查不等于应用重启后的界面可见状态 |

## 发布门

下面六项必须各自取证，不能互相替代：

1. rc5 Git 提交存在。
2. 提交已推送到远端。
3. 远端 CI 对该提交通过。
4. `v0.1.0-rc5` 标签在 GitHub 可见并指向正确提交。
5. GitHub prerelease 可见。
6. ZIP 与 `.sha256` 两个资产可见且下载哈希匹配。

当前只允许写“本地 rc5 候选已验证”，不允许写“rc5 已发布”。
