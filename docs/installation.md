# ChatMaker v0.1 安装说明

这版面向 Windows 64 位电脑、Codex 和 WorkBuddy。Nano 与 Uno 编译继续复用电脑里已经安装的 Mind+ 1.x 或 2.x；完全不安装 Mind+ 的独立工具链属于下一阶段。

## 先准备

```text
1. 安装 Python 3.11 或更高版本
2. 安装 Mind+ 1.x 或 2.x
3. 下载并解压 ChatMaker-0.1.0-rc4.zip
4. 把这个文件夹放在长期保留的位置，不要安装后删除或移动
5. 在解压后的 ChatMaker 文件夹打开 PowerShell
```

## 安装运行工具

```powershell
python -m pip install -e .
chatmaker-doctor
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

## 最小烟测

```powershell
chatmaker-nano --request-json '{"action":"doctor"}'
chatmaker-uno --request-json '{"action":"doctor"}'
chatmaker-esp32 --request-json '{"action":"doctor"}'
chatmaker-nano-examples --root examples/chatduino/nano
chatmaker-catalog --request-json '{"action":"search","query":"继电器","kind":"component"}'
chatmaker-serial --request-json '{"action":"list"}'
chatmaker-web-preview examples/chatweb/classroom-pulse.html
```

看到 Nano、Uno 或 ESP32 程序编译通过，只表示程序和编译环境通过。没有真实开发板时，烧录、串口、Wi-Fi、HTTP、断电重启和实体效果仍然是未验证状态。

## 校验下载包

```powershell
Get-FileHash .\ChatMaker-0.1.0-rc4.zip -Algorithm SHA256
Get-Content .\ChatMaker-0.1.0-rc4.zip.sha256
```

两处哈希必须完全一致。
