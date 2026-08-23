# ChatMaker 安装说明 / Installation

## 当前 Alpha 推荐安装方式

目前优先体验 GitHub `main`，让 AI 在终端执行下面四步即可：

```powershell
git clone https://github.com/Amasun93/ChatMaker.git
Set-Location ChatMaker
python -m pip install -e .
chatmaker-install auto
chatmaker-install doctor
```

`auto` 会根据电脑上实际存在的 AI 工作目录完成接入：宿主顶层只安装 ChatMaker，ChatDuino、ChatWeb、ChatCAD 作为它的内部 Skill，并登记通用 MCP。当前是快速迭代版；如需卸载或恢复，可运行 `chatmaker-install uninstall` 或 `chatmaker-install restore <transaction_id>`。下方签名 Core 章节是正式发布流程参考，普通 Alpha 体验不需要先构建发布包。
Alpha 使用可编辑源码安装，请保留克隆目录；更新时运行 `git pull`，再运行一次 `chatmaker-install auto`。

> rc5 已作为 [GitHub 公开预发布版](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc5) 发布。rc1–rc4 仍是独立历史发布；不要把 rc5 的验证结果倒写到旧版本记录中。
>
> rc5 is available as a [public GitHub prerelease](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc5). Public rc1–rc4 artifacts remain separate historical releases.

## 0. 当前源码：最小 Core 与渐进知识 / Current source: minimal Core and progressive knowledge

rc5 仍是当前公开下载。本节说明 rc5 之后的源码能力；后续 Core 按平台构建为 `ChatMaker-Core-0.1.0-rc5-<platform>.zip`，没有创建新的 GitHub Release。源码维护者可以运行：

rc5 remains the current public download. This section documents post-rc5 source behavior. Later Core artifacts are platform-specific: `ChatMaker-Core-0.1.0-rc5-<platform>.zip`; no new GitHub Release is created here. A source maintainer may run:

```powershell
python scripts/prepare_core_runtime.py --output .\prepared-runtime --platform-tag windows-amd64
python scripts/build_release.py --output dist --version 0.1.0-rc5 --platform-tag windows-amd64 --prepared-root .\prepared-runtime\windows-amd64 --release-sequence 1
python scripts/sign_core_release.py `
  --manifest .\dist\ChatMaker-Core-0.1.0-rc5-windows-amd64.zip.manifest.json `
  --private-key <受控发布环境中的官方私钥路径>
Get-FileHash .\dist\ChatMaker-Core-0.1.0-rc5-windows-amd64.zip -Algorithm SHA256
Get-Content .\dist\ChatMaker-Core-0.1.0-rc5-windows-amd64.zip.sha256
```

发布者会同时交付 canonical `.manifest.json` 与 detached `.manifest.json.sig.json`。用户应从可信官方渠道取得 `bootstrap.py` 和同目录的 `core_release_signature.py`；不要把尚未验签 ZIP 内的脚本当作信任起点。trusted bootstrap 先用内嵌官方 Ed25519 公钥验证 detached manifest，再只从同一只读文件描述符快照校验、解包 ZIP，并把版本化运行环境安装到 `~/.chatmaker/versions/`：

The publisher also ships a canonical `.manifest.json` and detached `.manifest.json.sig.json`. Obtain `bootstrap.py` and its sibling `core_release_signature.py` from the trusted official channel; do not treat a script extracted from the not-yet-authenticated ZIP as a trust anchor. The trusted bootstrap verifies the detached manifest with its embedded official Ed25519 key, validates and extracts one descriptor-backed ZIP snapshot, and installs under `~/.chatmaker/versions/`:

```powershell
python .\trusted-bootstrap\bootstrap.py `
  --archive .\dist\ChatMaker-Core-0.1.0-rc5-windows-amd64.zip `
  --checksum .\dist\ChatMaker-Core-0.1.0-rc5-windows-amd64.zip.sha256 `
  --release-manifest .\dist\ChatMaker-Core-0.1.0-rc5-windows-amd64.zip.manifest.json `
  --release-signature .\dist\ChatMaker-Core-0.1.0-rc5-windows-amd64.zip.manifest.json.sig.json
~\.chatmaker\bin\chatmaker-install.cmd doctor
```

macOS uses the same four evidence arguments with the matching `macos-x86_64` or `macos-arm64` archive; the resulting launcher is `~/.chatmaker/bin/chatmaker-install`. Linux is not part of this bootstrap release. Bootstrap and its Ed25519 verifier use only Python 3.11 standard-library code before Core is installed. Runtime installation is strictly local: pip receives `--isolated --no-index --find-links --require-hashes --no-deps`, and the venv does not inherit system site packages. A second trusted-bootstrap run derives the closed-world allowlist again from signed wheel `RECORD` files before running `auto --home`.

官方签名证明 release 来源；trusted bootstrap 的重跑只提供“当下这一刻”的漂移检查、隔离与修复。它不是 OS secure boot，也不承诺抵抗已经获得同用户任意写权限、能修改 verifier/launcher 或能在验证后继续竞态写入的攻击者。stable launcher 会 fail closed，并在 trusted bootstrap 重跑时修复，但 launcher 不会证明自身可信。

The official signature proves release origin. A trusted-bootstrap rerun provides point-in-time drift detection, quarantine, and repair only. This is not OS secure boot and does not resist an attacker who already has arbitrary same-user writes, can replace the verifier/launcher, or races after verification. The stable launcher fails closed and is repaired by trusted bootstrap, but does not prove its own trustworthiness.

Core 内有运行层、四个 Skill、schema、七块板卡记录、六个详细板卡知识索引、首批机械资料和当前案例。它没有扩展知识正文、`knowledge_sources/`、`tests/` 或开发缓存。`chatmaker-doctor` 通过只证明这些内置内容可读，不证明任何硬件效果。

The Core contains runtime code, four Skills, schemas, seven board records, six detailed board indexes, the first mechanical profiles, and current examples. It excludes extended knowledge bodies, `knowledge_sources/`, tests, and development caches. A successful doctor proves only that built-in software content is readable.

### 第一次自动读取 / First automatic read

下面的章节不在 Core 中。第一次执行时，reader 默认 `auto_install=true`，并调用幂等的 `ensure(pack_id)`：

The detailed section below is absent from Core. On first use, the reader defaults to `auto_install=true` and calls idempotent `ensure(pack_id)`:

```powershell
chatmaker-knowledge --request-json '{"action":"section","board_id":"arduino-nano-classic","consumer":"chatduino","section_id":"identify-and-safety"}'
chatmaker-pack status chatmaker-board-arduino-nano-classic-knowledge
```

只有官方签名注册表允许的只读 `knowledge` 包可以自动安装。ChatMaker 会先验证 Ed25519 签名、单调 sequence、有效期、不可变 commit URL、长度、SHA-256、manifest 和每个文件，再原子激活。第二次读取直接复用，不重复下载。

Only allowlisted, read-only `knowledge` packs may install automatically. ChatMaker checks the Ed25519 signature, monotonic sequence, validity window, immutable commit URL, length, SHA-256, manifest, and every file before atomic activation. A second read reuses the installed version without another download.

### 自动动作不会做什么 / What automatic installation never does

它不会安装或修改驱动、Mind+、Arduino Core、Node、Chromium、系统 PATH、安装钩子或管理员软件。需要这些外部环境时，ChatMaker 会停下来说明；用户仍需显式安装或批准。通用安装器处理四个 Skill 和可用宿主的 MCP 接入，不会顺便安装驱动或硬件工具链。

It never installs or changes drivers, Mind+, Arduino cores, Node, Chromium, PATH, hooks, or administrator-level software. External prerequisites remain explicit. The generic installer manages four Skills and available host MCP integration, not hardware toolchains.

### 离线、本地覆盖、更新与回滚 / Offline, overrides, update, and rollback

```powershell
chatmaker-pack list
chatmaker-pack cache
chatmaker-pack ensure chatmaker-board-arduino-nano-classic-knowledge --offline
chatmaker-pack update chatmaker-board-arduino-nano-classic-knowledge
chatmaker-pack rollback chatmaker-board-arduino-nano-classic-knowledge --version 1.0.0
```

- 已安装并重新校验通过的版本可以继续离线读取。精确缓存只有在随附的签名注册表 receipt 仍处于有效期内时，才能授权一次新的离线安装；receipt 过期后缓存不能授权新安装。从未下载或已过期的缺包会明确报错，不会猜内容。
- `update` 只接受注册表中的更高版本；失败时旧版本继续工作。`rollback` 只切换到本机已经完整验证的旧版本。
- 默认用户数据在 `~/.chatmaker/` 的 cache、store、state 等分区。不要手动修改官方 store；漂移内容会被隔离。
- 实验知识放在 `~/.chatmaker/overrides/`，或用 `CHATMAKER_PACKS_PATH` 指向独立目录。返回值会显示 `provenance=local_override`，避免把个人内容当成官方事实。
- 运行这些内容命令不会写 AI 宿主配置。只有 `chatmaker-install auto` 会在探测到真实宿主后接入顶层 ChatMaker、三个内部 Skill 和 MCP 条目，并继续使用事务备份恢复。

- An already installed version remains readable offline after full local revalidation. An exact cache can authorize a new offline install only while its signed registry receipt is still unexpired; an expired receipt cannot authorize a new install. Never-downloaded or expired missing content fails clearly instead of guessing.
- `update` accepts only a newer registry version and preserves the old active version on failure. `rollback` selects only a previously verified local version.
- User content lives under separated cache/store/state folders in `~/.chatmaker/`. Do not edit the official store by hand; drift is quarantined.
- Put experiments under `~/.chatmaker/overrides/`, or point `CHATMAKER_PACKS_PATH` at a separate directory. Results remain labelled `provenance=local_override`.
- Content commands never write Codex or WorkBuddy configuration. Only `chatmaker-install auto` changes detected host configuration by installing top-level ChatMaker, its three internal Skills, and the MCP entry, with the existing transactional backup and restore behavior.

## 1. 共同前置条件 / Common prerequisites

1. Windows x64、macOS Intel 或 Apple Silicon；安装对应平台的 Python 3.11。
2. 下载与电脑匹配的 ZIP、同名 `.sha256`、`.manifest.json` 和 detached `.manifest.json.sig.json`：Windows 为 `windows-amd64`，Mac 为 `macos-x86_64` 或 `macos-arm64`。
3. 从可信官方渠道取得 trusted-bootstrap 目录。先人工比对 SHA-256，再由 trusted bootstrap 验证官方签名和离线运行包。

Use the platform-specific Core ZIP and Python 3.11. Keep the ZIP, checksum, canonical manifest, detached signature, and official trusted-bootstrap directory together. No persistent source checkout or runtime network access is needed.

```powershell
Get-FileHash .\ChatMaker-Core-0.1.0-rc5-windows-amd64.zip -Algorithm SHA256
Get-Content .\ChatMaker-Core-0.1.0-rc5-windows-amd64.zip.sha256
python .\trusted-bootstrap\bootstrap.py `
  --archive .\ChatMaker-Core-0.1.0-rc5-windows-amd64.zip `
  --checksum .\ChatMaker-Core-0.1.0-rc5-windows-amd64.zip.sha256 `
  --release-manifest .\ChatMaker-Core-0.1.0-rc5-windows-amd64.zip.manifest.json `
  --release-signature .\ChatMaker-Core-0.1.0-rc5-windows-amd64.zip.manifest.json.sig.json
~\.chatmaker\bin\chatmaker-install.cmd doctor
```

两处 SHA-256 必须完全一致。`chatmaker-doctor` 校验资料包和四套 Skill，但不探测或证明真实硬件。

The two SHA-256 values must match exactly. `chatmaker-doctor` validates packs and Skills; it does not prove hardware.

## 2. Nano 与 Uno：Mind+ 前置条件 / Nano and Uno: Mind+ prerequisite

Nano 和 Uno 只复用已安装的 Mind+ 1.x 或 2.x。rc5 不会把官方 Arduino CLI 当成这两块板的默认后端。先安装并至少启动一次 Mind+，再运行：

Nano and Uno reuse an existing Mind+ 1.x or 2.x installation. Install and launch Mind+ once before these commands:

```powershell
chatmaker-nano --request-json '{"action":"doctor"}'
chatmaker-uno --request-json '{"action":"doctor"}'
chatmaker-avr-project --request-json '{"board_id":"arduino-uno-r3","code":"void setup(){} void loop(){}"}'
chatmaker-nano --request-json '{"action":"compile","sketch":"examples/chatduino/nano/blink"}'
chatmaker-uno --request-json '{"action":"compile","sketch":"examples/chatduino/uno/blink"}'
chatmaker-nano-examples --root examples/chatduino/nano
```

这些命令只编译，不上传。只有在明确要求 `compile-upload`、检测到唯一合格有线端口并通过安全检查时，运行层才可能进入上传阶段。

These examples compile only. Upload is a separate gate and is considered only for an explicit `compile-upload` request with one safe wired port.

`chatmaker-avr-project` 是 Nano/Uno 的连续入口：它先检查环境，再编译；只有串口唯一且安全时才烧录。没有接板时会返回 `compiled-awaiting-hardware`，不会把编译完成写成烧录成功。

### 星核板 v4.2.2 / Starcore v4.2.2

星核板使用已经安装的 Mind+ 1.8 当前目标。Mind+ 2.0 目标只作为历史资料保留：

```powershell
chatmaker-starcore --request-json '{"action":"doctor"}'
chatmaker-starcore --request-json '{"action":"compile","sketch":"examples/chatduino/starcore/blink"}'
```

烧录前必须确认实体板为星核板 v4.2.2，并且只剩一个合格的非蓝牙有线串口。没有实体板时上传、重启、串口和实物效果保持 `unverified`。

### 自动识别星核板和两代掌控板

```powershell
chatmaker-board-identify --request-json '{"action":"identify","allow_temporary_firmware":true}'
```

识别会先读取安全线索。仍无法区分时，它可以在完整备份后写入临时识别程序，并在读取后恢复原 Flash；恢复没有验证成功时会停止并保留备份。电子证据仍重叠时，AI 会告诉用户去哪里看型号，最后请用户拍正反面照片。经典掌控板和掌控板 3.0 使用不同知识索引与工具链；不得互相替代。

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
chatmaker-web-preview examples/chatweb/serial-device-console.html
chatmaker-cad --request-json '{"action":"generate","mode":"chat2d","board_id":"arduino-uno-r3","project_name":"uno-box","output_dir":"uno-box"}'
chatmaker-cad --request-json '{"action":"generate","mode":"chat3d","board_id":"idmc-0001-starcore-v4-2-2","project_name":"starcore-case","output_dir":"starcore-case"}'
```

`chatmaker-web-preview` 默认只监听 `127.0.0.1`，按 Ctrl+C 结束。高级方向和游乐场必须显式传入 `--advanced`。`page_html.h` 是生成物；只编辑 `examples/chatweb/esp32-ap-control.html`。

`chatmaker-web-preview` binds to `127.0.0.1` by default; stop it with Ctrl+C. Advanced directions require explicit `--advanced`. Edit the HTML source, not the generated header.

## 5. 一条安装命令与能力结果 / One installer command and capability results

```powershell
chatmaker-install auto --dry-run
chatmaker-install auto
chatmaker-install doctor
```

安装器先只读探测操作系统、Python、终端、浏览器、串口、Mind+、已存在的 AI 工作目录线索，以及高级入口提供的显式路径。它不会要求你选择宿主；发现的宿主会一起安装四个 Skill，可用宿主还会登记共享 MCP：`python -m chatmaker.integrations.mcp`。无关 MCP 条目会保留。

每个命令输出一份 JSON，至少包含 `success`、`status`、`environment`、`hosts`、`changes`、`unchanged`、`next_actions` 与 `transaction_id`。先运行 `auto --dry-run` 查看计划；`auto` 执行可逆的用户目录改动；随后重启检测到的宿主应用。

没有板卡、合格有线串口或 Mind+ 是受限能力状态，不是安装失败。此时仍可使用 Core、Skill 和可用的宿主集成；只有需要 Nano / Uno 编译或上传时，按 JSON 的 `next_actions` 安装并启动 Mind+。本阶段不会安装驱动、Mind+、Arduino Core、浏览器，也不会预装所有板卡知识包。

对其他宿主，才使用绝对路径的高级入口，例如：

```powershell
chatmaker-install auto --skill-root D:\OtherHost\skills
chatmaker-install auto --skill-root D:\OtherHost\skills --mcp-config D:\OtherHost\mcp.json
```

恢复与卸载由同一个事务管理。`restore` 必须使用 `auto` 输出的 `transaction_id`：

```powershell
chatmaker-install restore <transaction_id>
chatmaker-install uninstall
```

`restore` 回到该交易开始前的完整状态；`uninstall` 只移除 ChatMaker 当前受管内容，并保留之后新增的无关 MCP 项。

如需排查 WorkBuddy 所登记的共享 MCP（这不是另一个安装流程），可向它发送一次 JSON-RPC `tools/list` 烟测；该 stdio 服务不接受 `--help`：

```powershell
'{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' | chatmaker-workbuddy-mcp
```

For a direct smoke test of the shared MCP registered for WorkBuddy (not a separate installation flow), send it one JSON-RPC `tools/list` request. This stdio service does not accept `--help`.

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

需要查看普通 CLI 参数时，可对这些命令分别传入 `--help`：`chatmaker-doctor`、`chatmaker-catalog`、`chatmaker-route`、`chatmaker-board-identify`、`chatmaker-nano`、`chatmaker-uno`、`chatmaker-avr-project`、`chatmaker-starcore`、`chatmaker-esp32`、`chatmaker-nano-examples`、`chatmaker-serial`、`chatmaker-cad`、`chatmaker-install`、`chatmaker-pack`、`chatmaker-knowledge`、`chatmaker-web`、`chatmaker-web-plan`、`chatmaker-web-playground`、`chatmaker-web-preview`、`chatmaker-web-embed`。

For ordinary CLI usage, pass `--help` to the commands listed above. `chatmaker-workbuddy-mcp` is different: it is a JSON-RPC stdio service that waits for input and must not be invoked with `--help`. Run `chatmaker-install doctor` to inspect detected integrations safely.

## 7. 证据边界 / Evidence boundary

编译、上传、串口、浏览器、网络、断电重启和物理效果是不同的验收门。编译成功不能证明烧录或实物效果；浏览器模拟不能证明 ESP32 SoftAP、HTTP 或元器件工作。rc5 在没有匹配硬件证据时会保留这些状态为 `unverified`。

Compile, upload, serial, browser, network, power-cycle, and physical effects are separate gates. Compilation does not prove upload or physical behavior; browser simulation does not prove ESP32 SoftAP, HTTP, or components. rc5 leaves those states `unverified` without matching evidence.
