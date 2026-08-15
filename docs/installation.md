# ChatMaker v0.1.0-rc5 安装说明 / Installation

> rc5 已作为 [GitHub 公开预发布版](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc5) 发布。rc1–rc4 仍是独立历史发布；不要把 rc5 的验证结果倒写到旧版本记录中。
>
> rc5 is available as a [public GitHub prerelease](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc5). Public rc1–rc4 artifacts remain separate historical releases.

## 0. 当前源码：最小 Core 与渐进知识 / Current source: minimal Core and progressive knowledge

rc5 仍是当前公开下载。本节说明 rc5 之后的源码能力；Task 7 只在本地构建和验证 `ChatMaker-Core-0.1.0-rc5.zip`，没有创建新的 GitHub Release。源码维护者可以运行：

rc5 remains the current public download. This section documents post-rc5 source behavior. Task 7 builds and verifies `ChatMaker-Core-0.1.0-rc5.zip` locally and does not create a new GitHub Release. A source maintainer may run:

```powershell
python scripts/build_release.py --output dist --version 0.1.0-rc5
Get-FileHash .\dist\ChatMaker-Core-0.1.0-rc5.zip -Algorithm SHA256
Get-Content .\dist\ChatMaker-Core-0.1.0-rc5.zip.sha256
```

两处 SHA-256 一致后，把 Core 解压到长期保留的目录，再创建独立虚拟环境：

After the two SHA-256 values match, extract the Core into a persistent directory and create a dedicated virtual environment:

```powershell
Expand-Archive .\dist\ChatMaker-Core-0.1.0-rc5.zip -DestinationPath .\core-check
Set-Location .\core-check\ChatMaker-Core-0.1.0-rc5
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
chatmaker-doctor
chatmaker-install-codex install
# 或 / or: chatmaker-install-workbuddy install
```

Core 内有运行层、三个 Skill、schema、3/12/14 条规范记录、三个紧凑索引和当前案例。它没有详细 Wiki 正文、`knowledge_sources/`、`tests/`、开发缓存或已构建的可选 `.cmpack`。`chatmaker-doctor` 通过只证明这些内置内容可读，不证明任何硬件效果。

The Core contains runtime code, three Skills, schemas, the canonical 3/12/14 records, three compact indexes, and current examples. It excludes detailed Wiki bodies, `knowledge_sources/`, `tests/`, development caches, and built optional `.cmpack` artifacts. A successful doctor proves only that built-in software content is readable.

### 第一次自动读取 / First automatic read

下面的章节不在 Core 中。第一次执行时，reader 默认 `auto_install=true`，并调用幂等的 `ensure(pack_id)`：

The detailed section below is absent from Core. On first use, the reader defaults to `auto_install=true` and calls idempotent `ensure(pack_id)`:

```powershell
chatmaker-llmwiki --request-json '{"action":"section","board_id":"arduino-nano-classic","consumer":"chatduino","section_id":"identify-and-safety"}'
chatmaker-pack status chatmaker-board-arduino-nano-classic-wiki
```

只有官方签名注册表允许的只读 `knowledge` 包可以自动安装。ChatMaker 会先验证 Ed25519 签名、单调 sequence、有效期、不可变 commit URL、长度、SHA-256、manifest 和每个文件，再原子激活。第二次读取直接复用，不重复下载。

Only allowlisted, read-only `knowledge` packs may install automatically. ChatMaker checks the Ed25519 signature, monotonic sequence, validity window, immutable commit URL, length, SHA-256, manifest, and every file before atomic activation. A second read reuses the installed version without another download.

### 自动动作不会做什么 / What automatic installation never does

它不会安装或修改驱动、Mind+、Arduino Core、Node、Chromium、系统 PATH、安装钩子、管理员软件或 WorkBuddy MCP 配置。需要这些外部环境时，ChatMaker 会停下来说明；用户仍需显式安装或批准。Codex / WorkBuddy 安装器只处理三个 Skill（以及 WorkBuddy 自己的 MCP 条目），不会顺便安装或更新知识包。

It never installs or changes drivers, Mind+, Arduino cores, Node, Chromium, PATH, hooks, administrator-level software, or WorkBuddy MCP configuration. External prerequisites remain explicit. Codex and WorkBuddy installers manage only the three Skills (plus WorkBuddy's own MCP entry), never knowledge content.

### 离线、本地覆盖、更新与回滚 / Offline, overrides, update, and rollback

```powershell
chatmaker-pack list
chatmaker-pack cache
chatmaker-pack ensure chatmaker-board-arduino-nano-classic-wiki --offline
chatmaker-pack update chatmaker-board-arduino-nano-classic-wiki
chatmaker-pack rollback chatmaker-board-arduino-nano-classic-wiki --version 1.0.0
```

- 已安装并重新校验通过的版本可以继续离线读取。精确缓存只有在随附的签名注册表 receipt 仍处于有效期内时，才能授权一次新的离线安装；receipt 过期后缓存不能授权新安装。从未下载或已过期的缺包会明确报错，不会猜内容。
- `update` 只接受注册表中的更高版本；失败时旧版本继续工作。`rollback` 只切换到本机已经完整验证的旧版本。
- 默认用户数据在 `~/.chatmaker/` 的 cache、store、state 等分区。不要手动修改官方 store；漂移内容会被隔离。
- 实验知识放在 `~/.chatmaker/overrides/`，或用 `CHATMAKER_PACKS_PATH` 指向独立目录。返回值会显示 `provenance=local_override`，避免把个人内容当成官方事实。
- 运行这些内容命令不会写 Codex 或 WorkBuddy 配置。主机配置只有显式 host install/uninstall 才会改动，并继续使用备份恢复。

- An already installed version remains readable offline after full local revalidation. An exact cache can authorize a new offline install only while its signed registry receipt is still unexpired; an expired receipt cannot authorize a new install. Never-downloaded or expired missing content fails clearly instead of guessing.
- `update` accepts only a newer registry version and preserves the old active version on failure. `rollback` selects only a previously verified local version.
- User content lives under separated cache/store/state folders in `~/.chatmaker/`. Do not edit the official store by hand; drift is quarantined.
- Put experiments under `~/.chatmaker/overrides/`, or point `CHATMAKER_PACKS_PATH` at a separate directory. Results remain labelled `provenance=local_override`.
- Content commands never write Codex or WorkBuddy configuration. Only explicit host install/uninstall changes host configuration, with the existing backup and restore behavior.

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

当前源码的 WorkBuddy stdio 应报告服务版本 `1.8.0` 和 24 个工具，包括 `llmwiki_get`。安装器会备份同名 Skill 或 WorkBuddy 配置，并保留无关 MCP。知识包更新不会触碰该配置。安装后重启对应应用。恢复原状：

Current source should report WorkBuddy stdio server `1.8.0` with 24 tools, including `llmwiki_get`. The installers back up replaced Skills/configuration and preserve unrelated MCP entries. Knowledge updates do not touch that configuration. Restart the host application after installation. To restore:

```powershell
chatmaker-install-codex uninstall
chatmaker-install-workbuddy uninstall
```

## 6. 开发与浏览器验证 / Development and browser verification

历史 rc5 发布包包含 Playwright 清单和浏览器测试；新的最小 Core 不包含开发测试。源码贡献者运行浏览器验证仍需要完整仓库、Node.js 22（或兼容版本）和网络可用的首次浏览器安装：

The historical rc5 archive includes Playwright manifests and tests; the new minimal Core excludes development tests. Source contributors need the full repository and Node.js 22 (or compatible) for browser verification:

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
