# ChatMaker v0.1.0-rc1 发布候选验证

## 构建规则

- 使用 `scripts/build_release.py` 生成固定文件顺序与固定 ZIP 时间戳的源码包。
- 自动排除 `.git`、`__pycache__`、`.playwright-cli` 和 `*.egg-info`。
- 同一工作树连续构建两次，测试要求 SHA-256 完全一致。
- 构建同时生成 `ChatMaker-v0.1.0-rc1.zip.sha256`。

## 独立哈希检查

PowerShell `Get-FileHash -Algorithm SHA256` 的结果与 `.sha256` 文件记录完全一致。最终哈希以与 GitHub 预发布同时上传的 sidecar 文件为准，避免把哈希写回源码后改变 ZIP 本身。

## 解压后安装检查

候选 ZIP 被解压到一个新的临时目录，并在新的 Python 3.11 虚拟环境执行：

```text
pip install -e <解压后的 ChatMaker-0.1.0-rc1>
chatmaker-doctor
chatmaker-install-codex install / doctor / uninstall
chatmaker-install-workbuddy install / doctor / uninstall
WorkBuddy stdio MCP ping
```

结果：

- 安装版本：`chatmaker-0.1.0rc1`
- 3 个板卡、8 种元器件、7 个配方：通过。
- ChatMaker、ChatDuino、ChatWeb Skill：通过。
- Codex 三个 Skill：安装、doctor、卸载通过。
- WorkBuddy 三个 Skill与 MCP：安装、doctor、stdio ping、卸载通过。
- 解压包不依赖当前仓库的未打包文件完成上述检查。

## 仍未由候选包证明

- 没有连接有线 Nano，因此没有烧录、串口运行、断电重启和 LED 实物效果证据。
- 没有把模拟硬件界面当作真实设备通信。
- 完全独立于 Mind+ 的编译与驱动环境属于下一阶段。
