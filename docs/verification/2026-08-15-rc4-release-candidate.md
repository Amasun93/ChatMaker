# ChatMaker v0.1.0-rc4 发布候选验收

## 发布内容

- Python 包版本：`0.1.0rc4`
- 发布目录：`ChatMaker-0.1.0-rc4`
- 板卡、元器件、配方：3 / 12 / 12
- WorkBuddy MCP：`chatmaker-hardware` 1.4.0，共 18 个工具
- 新增能力：Arduino Uno Rev3 独立 Mind+ 编译、端口和固定 115200 上传流程

## 本地验证

- `python -m unittest discover -s tests -v`：84 项通过。
- `python runtime/doctor.py`：资料包和三套 Skill 通过。
- `python scripts/validate_skills.py`：ChatMaker、ChatDuino、ChatWeb 通过。
- 同一发布源连续构建两次，两份 ZIP 的 SHA-256 完全一致。
- PowerShell `Get-FileHash` 与随包 `.sha256` 文件完全一致。

最终哈希只写入与 GitHub Release 同时上传的 `.sha256` 文件，避免把哈希写回源码后改变 ZIP 本身。

## 全新解压验证

候选 ZIP 解压到新的临时目录，并在新的 Python 3.11 虚拟环境完成：

```text
pip install -e <解压后的 ChatMaker-0.1.0-rc4>
chatmaker-doctor
chatmaker-uno doctor
chatmaker-uno compile Uno Blink
chatmaker-install-codex install / doctor / uninstall
chatmaker-install-workbuddy install / doctor / uninstall
```

结果：

- 安装版本为 `chatmaker 0.1.0rc4`。
- Uno doctor 找到 Mind+ 1.x 和 2.x，并正确报告没有有线烧录端口。
- 从解压包路径使用 `mindplus:avr:uno` 真实编译 Uno Blink 成功。
- Codex 和 WorkBuddy 的三个 Skill 均可逆安装，检查通过后可恢复。

## 证据边界

- 当前只有 6 个蓝牙串口，没有有线 Uno 或 Nano。
- 没有执行 Uno 或 Nano 固件烧录。
- 串口标记、断电重启、LED 和其他物理效果均未验证。
- ESP32 DevKit V1 和完全不安装 Mind+ 的独立工具链仍未进入本候选包。
