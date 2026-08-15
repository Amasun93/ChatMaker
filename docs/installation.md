# ChatMaker v0.1.0-rc5 安装说明 / Installation

> rc5 已作为 [GitHub 公开预发布版](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc5) 发布。rc1–rc4 仍是独立历史发布；不要把 rc5 的验证结果倒写到旧版本记录中。
>
> rc5 is available as a [public GitHub prerelease](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc5). Public rc1–rc4 artifacts remain separate historical releases.

## 1. 共同前置条件 / Common prerequisites

1. Windows 64 位；Python 3.11 或更高版本，并可使用 `python -m pip`。
2. 下载 `ChatMaker-0.1.0-rc5.zip` 与同名 `.sha256` 到同一个下载目录。
3. 先在下载目录校验 ZIP，再解压并进入长期保留的源码目录。安装器和 editable install 会引用该目录，不要在使用期间移动或删除它。

Windows 64-bit and Python 3.11+ are required. Start in the download directory that contains both the ZIP and sidecar. Verify first; only then extract and enter the persistent source directory.

```powershell
Get-FileHash .\ChatMaker-0.1.0-rc5.zip -Algorithm SHA256
Get-Content .\ChatMaker-0.1.0-rc5.zip.sha256
Expand-Archive .\ChatMaker-0.1.0-rc5.zip -DestinationPath .
Set-Location .\ChatMaker-0.1.0-rc5
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
chatmaker-doctor
```

两处 SHA-256 必须完全一致。`chatmaker-doctor` 校验资料包和三套 Skill，但不探测或证明真实硬件。

The two SHA-256 values must match exactly. `chatmaker-doctor` validates packs and Skills; it does not prove hardware.

## 2. Nano 与 Uno：Mind+ 前置条件 / Nano and Uno: Mind+ prerequisite

Nano 和 Uno 只复用已安装的 Mind+ 1.x 或 2.x。rc5 不会把官方 Arduino CLI 当成这两块板的默认后端。先安装并至少启动一次 Mind+，再运行：

Nano and Uno reuse an existing Mind+ 1.x or 2.x installation. Install and launch Mind+ once before these commands:

```powershell
chatmaker-nano --request-json '{"action":"doctor"}'
chatmaker-uno --request-json '{"action":"doctor"}'
chatmaker-nano --request-json '{"action":"compile","sketch":"examples/chatduino/nano/blink"}'
chatmaker-uno --request-json '{"action":"compile","sketch":"examples/chatduino/uno/blink"}'
chatmaker-nano-examples --root examples/chatduino/nano
```

这些命令只编译，不上传。只有在明确要求 `compile-upload`、检测到唯一合格有线端口并通过安全检查时，运行层才可能进入上传阶段。

These examples compile only. Upload is a separate gate and is considered only for an explicit `compile-upload` request with one safe wired port.

## 3. ESP32：官方 Arduino CLI 前置条件 / ESP32: official Arduino CLI prerequisite

ESP32 不使用 Mind+ CLI。请安装 Arduino IDE 2（包含官方 Arduino CLI）或独立的官方 Arduino CLI。rc5 只接受 `DOIT ESP32 DEVKIT V1 + ESP-WROOM-32`、官方 Core `esp32:esp32@3.3.11` 和 FQBN `esp32:esp32:esp32doit-devkit-v1`。

ESP32 never uses a Mind+ CLI. Install Arduino IDE 2 or a standalone official Arduino CLI. rc5 accepts only the exact board/core/FQBN above.

```powershell
chatmaker-esp32 --request-json '{"action":"prepare-environment"}'
chatmaker-esp32 --request-json '{"action":"doctor"}'
chatmaker-esp32 --request-json '{"action":"compile","board_profile":"doit-esp32-devkit-v1-wroom32","sketch":"examples/chatduino/esp32/blink-external-led"}'
chatmaker-esp32 --request-json '{"action":"compile","board_profile":"doit-esp32-devkit-v1-wroom32","sketch":"examples/chatduino/esp32/ap-led-sensor"}'
```

`prepare-environment` 只安装锁定的官方 Core，不追随 `latest`，也不会静默降级未知或更高版本。上面两条是编译命令；它们不会烧录开发板。

`prepare-environment` installs only the locked official core. The two example commands are compile-only and never upload firmware.

## 4. 路由、资料和网页命令 / Router, catalog, and web commands

以下示例覆盖 rc5 中的可执行路由、创意规划、默认单页生成、显式高级游乐场、本地预览和 ESP32 页面嵌入。

```powershell
chatmaker-catalog --request-json '{"action":"search","query":"继电器","kind":"component"}'
chatmaker-route --request-json '{"hardware":{"board":"arduino-nano-classic"}}'
chatmaker-web-plan --brief-json '{"kind":"classroom-tool","idea":"收集课堂反馈","audience_scene":"学生下课前使用","desired_feeling":"清楚而轻松","primary_action":"选择最需要重讲的一步"}'
chatmaker-web --request-json '{"kind":"classroom-tool","title":"课堂脉冲","prompt":"今天哪一步最需要再讲一次？","primary_label":"我需要再讲一次","direction_id":"editorial-signal"}' --output classroom-pulse.html
chatmaker-web-plan --brief-json '{"kind":"classroom-tool","idea":"收集课堂反馈","audience_scene":"学生下课前使用","desired_feeling":"清楚而轻松","primary_action":"选择最需要重讲的一步"}' --advanced
chatmaker-web-playground --kind classroom-tool --title "课堂方向游乐场" --brief "比较更多课堂反馈方向" --output advanced-playground.html --advanced
chatmaker-web-preview classroom-pulse.html
chatmaker-web-embed examples/chatweb/esp32-ap-control.html examples/chatduino/esp32/ap-led-sensor/page_html.h --symbol CHATMAKER_AP_PAGE
```

`chatmaker-web-preview` 默认只监听 `127.0.0.1`，按 Ctrl+C 结束。高级方向和游乐场必须显式传入 `--advanced`。`page_html.h` 是生成物；只编辑 `examples/chatweb/esp32-ap-control.html`。

`chatmaker-web-preview` binds to `127.0.0.1` by default; stop it with Ctrl+C. Advanced directions require explicit `--advanced`. Edit the HTML source, not the generated header.

## 5. 串口、WorkBuddy 和 Codex / Serial, WorkBuddy, and Codex

```powershell
chatmaker-serial --request-json '{"action":"list"}'
'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05"}}' | chatmaker-workbuddy-mcp
'{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' | chatmaker-workbuddy-mcp
chatmaker-install-codex install
chatmaker-install-codex doctor
chatmaker-install-workbuddy install
chatmaker-install-workbuddy doctor
```

WorkBuddy stdio 应报告服务版本 `1.7.0` 和 23 个工具。安装器会备份同名 Skill 或 WorkBuddy 配置，并保留无关 MCP。安装后重启对应应用。恢复原状：

WorkBuddy stdio should report server version `1.7.0` and 23 tools. The installers back up replaced Skills/configuration and preserve unrelated MCP entries. Restart the host application after installation. To restore:

```powershell
chatmaker-install-codex uninstall
chatmaker-install-workbuddy uninstall
```

## 6. 开发与浏览器验证 / Development and browser verification

发布包包含 Playwright 清单和浏览器测试，但不会预装 Node.js 或 Chromium。运行浏览器验证需要 Node.js 22（或兼容版本）和网络可用的首次浏览器安装：

The archive includes Playwright manifests and tests, but not Node.js or Chromium. For browser verification, install Node.js 22 (or a compatible version), then run:

```powershell
python scripts/validate_skills.py
python -m unittest discover -s tests -v
npm ci
npx playwright install chromium
npm run test:browser
```

需要查看普通 CLI 参数时，可对这些命令分别传入 `--help`：`chatmaker-doctor`、`chatmaker-catalog`、`chatmaker-route`、`chatmaker-nano`、`chatmaker-uno`、`chatmaker-esp32`、`chatmaker-nano-examples`、`chatmaker-serial`、`chatmaker-install-workbuddy`、`chatmaker-install-codex`、`chatmaker-web`、`chatmaker-web-plan`、`chatmaker-web-playground`、`chatmaker-web-preview`、`chatmaker-web-embed`。

For ordinary CLI usage, pass `--help` to the commands listed above. `chatmaker-workbuddy-mcp` is different: it is a JSON-RPC stdio service that waits for input and must not be invoked with `--help`. Use the `initialize` / `tools/list` pipe shown in section 5 for a direct smoke test, or run `chatmaker-install-workbuddy doctor` to inspect the installed WorkBuddy integration safely.

## 7. 证据边界 / Evidence boundary

编译、上传、串口、浏览器、网络、断电重启和物理效果是不同的验收门。编译成功不能证明烧录或实物效果；浏览器模拟不能证明 ESP32 SoftAP、HTTP 或元器件工作。rc5 在没有匹配硬件证据时会保留这些状态为 `unverified`。

Compile, upload, serial, browser, network, power-cycle, and physical effects are separate gates. Compilation does not prove upload or physical behavior; browser simulation does not prove ESP32 SoftAP, HTTP, or components. rc5 leaves those states `unverified` without matching evidence.
