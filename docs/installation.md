# ChatMaker v0.1 安装说明

本文同时说明“已发布的 rc4 候选包”和“正在开发的仓库版”。两者不是同一套功能，不能把开发版命令当成 rc4 已有能力。

## 已发布：`ChatMaker-0.1.0-rc4.zip`

rc4 面向 Windows 64 位电脑、Codex 和 WorkBuddy，包含 Nano 与 Uno 的 Mind+ 1.x/2.x 工作流。它**不包含**新的 ESP32 `prepare-environment` 命令，也不包含 `chatmaker-web-embed` 页面嵌入命令。

```text
1. 安装 Python 3.11 或更高版本
2. 安装 Mind+ 1.x 或 2.x（Nano 与 Uno 必需）
3. 下载并解压 ChatMaker-0.1.0-rc4.zip
4. 把文件夹放在长期保留的位置，不要安装后删除或移动
5. 在解压后的 ChatMaker 文件夹打开 PowerShell
```

```powershell
python -m pip install -e .
chatmaker-doctor
chatmaker-nano --request-json '{"action":"doctor"}'
chatmaker-uno --request-json '{"action":"doctor"}'
```

## 当前开发版：ESP32 与网页嵌入

需要新的 ESP32 或网页嵌入能力时，请从公开仓库 checkout 后以 editable 方式安装，而不是使用 rc4 ZIP：

```powershell
git clone https://github.com/Amasun93/ChatMaker.git
cd ChatMaker
python -m pip install -e .
chatmaker-doctor
```

ESP32 开发版需要 Arduino IDE 2（其官方 Arduino CLI）或独立的官方 Arduino CLI；不能借用 Mind+ 的 CLI。Nano 和 Uno 仍继续复用 Mind+ 1.x/2.x，不受此限制。

ESP32 只接受 `DOIT ESP32 DEVKIT V1 + ESP-WROOM-32 + esp32:esp32:esp32doit-devkit-v1` 这一个精确目标。准备命令只安装 ChatMaker 已验证的 `esp32:esp32@3.3.11`，不会自动追最新版，也不会静默替换更高、未知或名称近似的版本：

```powershell
chatmaker-esp32 --request-json '{"action":"prepare-environment"}'
```

## 安装到 Codex

```powershell
chatmaker-install-codex install
chatmaker-install-codex doctor
```

安装器复制 `chatmaker`、`chatduino`、`chatweb` 三个 Skill。若存在同名 Skill，会先备份并生成恢复清单。安装后重启 Codex。

需要恢复原状时：

```powershell
chatmaker-install-codex uninstall
```

## 安装到 WorkBuddy

```powershell
chatmaker-install-workbuddy install
chatmaker-install-workbuddy doctor
```

安装器会备份 `~/.workbuddy/mcp.json`，保留其他 MCP，只更新 ChatMaker 使用的兼容入口，并复制三个 Skill。这个入口同时提供 Nano、Uno、ESP32、资料目录和串口工具。安装后重启 WorkBuddy。

需要恢复原配置和原 Skill 时：

```powershell
chatmaker-install-workbuddy uninstall
```

## 开发版最小烟测

```powershell
chatmaker-nano --request-json '{"action":"doctor"}'
chatmaker-uno --request-json '{"action":"doctor"}'
chatmaker-esp32 --request-json '{"action":"prepare-environment"}'
chatmaker-esp32 --request-json '{"action":"doctor"}'
chatmaker-nano-examples --root examples/chatduino/nano
chatmaker-catalog --request-json '{"action":"search","query":"继电器","kind":"component"}'
chatmaker-serial --request-json '{"action":"list"}'
chatmaker-web-embed examples/chatweb/esp32-ap-control.html examples/chatduino/esp32/ap-led-sensor/page_html.h --symbol CHATMAKER_AP_PAGE
chatmaker-web-preview examples/chatweb/classroom-pulse.html
```

看到 Nano、Uno 或 ESP32 程序编译通过，只表示程序和编译环境通过。没有真实开发板时，烧录、串口、Wi-Fi、HTTP、断电重启和实体效果仍然是未验证状态。

`chatmaker-web-embed` 会把单文件网页嵌入到 ESP32 固件头文件里。`examples/chatweb/esp32-ap-control.html` 是唯一可编辑页面源，生成出来的 `examples/chatduino/esp32/ap-led-sensor/page_html.h` 不要手改。

## 校验下载包

```powershell
Get-FileHash .\ChatMaker-0.1.0-rc4.zip -Algorithm SHA256
Get-Content .\ChatMaker-0.1.0-rc4.zip.sha256
```

两处哈希必须完全一致。
