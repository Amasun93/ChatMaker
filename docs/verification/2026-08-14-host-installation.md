# Codex 与 WorkBuddy 安装验收

## 验收范围

- Codex：三个 Skill 的安装、doctor、Nano Blink 编译、卸载恢复。
- WorkBuddy：三个 Skill、MCP 配置合并、真实 stdio MCP、Nano Blink 编译、卸载恢复。
- 运行工具：当前发布候选继续使用已经安装的 Mind+ 1.x/2.x。

## 干净目录闭环

在新的临时 Codex Home 和 WorkBuddy Home 中执行：

1. 安装 ChatMaker、ChatDuino、ChatWeb。
2. doctor 确认三个 Skill 就绪。
3. Codex 路线调用 CLI，使用 Mind+ 2.x 编译 Blink。
4. WorkBuddy 路线从安装后生成的 `mcp.json` 启动 stdio MCP，调用 `nano_compile` 编译 Blink。
5. 分别卸载。
6. Codex 临时 Skill 数量恢复为 0；原本不存在的 WorkBuddy 配置恢复为不存在。

两次编译均使用：

```text
backend: mindplus-2-cli
fqbn: mindplus:avr:nano:cpu=atmega328
compile success: true
```

## 当前电脑真实安装

### Codex

- 安装目录：`C:\Users\asus\.codex\skills\chatmaker|chatduino|chatweb`
- 安装清单：`C:\Users\asus\.codex\chatmaker-codex-install.json`
- doctor：三个 Skill 全部 `ready: true`
- Blink 编译：成功，Mind+ 2.x，Nano ATmega328P FQBN。

### WorkBuddy

安装前检测到 6 个 MCP。安装器只替换同名 `arduino-nano-mindplus`，保留另外 5 个，并先备份原 `mcp.json`。

- 安装目录：`C:\Users\asus\.workbuddy\skills\chatmaker|chatduino|chatweb`
- 配置备份：`C:\Users\asus\.workbuddy\mcp.json.backup-1786702496978737800`
- 安装清单：`C:\Users\asus\.workbuddy\chatmaker-workbuddy-install.json`
- MCP 初始化协议：`2025-03-26`
- MCP 工具数量：5
- Blink `nano_compile`：成功，`isError: false`
- 编译后端：Mind+ 2.x

第一次真实复制时，Windows 拒绝把临时目录重命名为 `chatduino`，暴露了部分安装风险。随后新增并验证：

- 中途失败自动回滚已经激活的 Skill。
- Windows 目录重命名被拒绝时，安全回退为复制后清理临时目录。
- 真实 stdio MCP 子进程 ping 回归测试。

第一次失败产生的文件没有删除，已移动到：

```text
C:\Users\asus\.workbuddy\chatmaker-failed-install-20260814
```

## 证据边界

- Skill 文件安装：已验证。
- MCP 配置保留与替换：已验证。
- Codex / WorkBuddy Nano 编译：已验证。
- 卸载恢复：在隔离目录已验证；真实用户目录未执行卸载，因为当前目标是保留安装。
- 宿主重启后的界面发现：需要重启 Codex 和 WorkBuddy 后确认。
- Nano 烧录、串口、断电重启和实物效果：没有有线 Nano，未验证。
