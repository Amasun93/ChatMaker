# Nano Mind+ 只读迁移清单

## 权威来源

```text
仓库
D:\Projects\26博荟暑假班\自研硬件Skill开发\05_发布包\arduino-nano-mindplus-github

内容根目录
arduino-nano-mindplus

提交
9ebc6bff16529557aa2cebe661755cf6c51d79ed

远端
https://github.com/Amasun93/arduino-nano-mindplus
origin/main = 9ebc6bf
```

选择依据如下。

- GitHub 交付目录和 `arduino-nano-mindplus-v1.2.0` 的 18 个发布文件哈希一致。
- GitHub 交付目录另外保留 3 个测试文件，共 21 个有效文件。
- GitHub 交付目录和开发目录均运行 33 项测试，结果全部通过。
- 开发目录的运行脚本和测试与 GitHub 版本一致，但 6 个示例、5 份硬件参考和 `agents/openai.yaml` 哈希不同。
- 带提交历史且与 v1.2 发布包一致的 GitHub `9ebc6bf` 作为迁移真相源。开发目录只用于交叉核对，不从中混合挑选文件。

## 迁移边界

旧仓库保持只读，不提交、不切换分支、不覆盖文件。ChatMaker 按自己的共享运行层和三个 Skill 边界重新组织能力。

| 原文件 | ChatMaker 目标 | 处理方式 |
| --- | --- | --- |
| `scripts/nano_mindplus_bridge.py` | `runtime/chatmaker/hardware/nano_mindplus.py` | 迁移全部环境、编译、端口和烧录行为，保留结构化结果 |
| `tests/test_nano_bridge.py` | `tests/hardware/test_nano_mindplus.py` | 先迁移 25 项运行层回归测试，再适配包导入 |
| `scripts/workbuddy_mcp_server.py` | `runtime/chatmaker/integrations/workbuddy_mcp.py` | 保留 5 个 Nano 工具，后续并入 ChatMaker 共用 MCP |
| `scripts/install_workbuddy_bridge.py` | `runtime/chatmaker/installers/workbuddy.py` | 保留备份和已有 MCP 配置，改为 ChatMaker 安装器的一部分 |
| `tests/test_workbuddy_bridge.py` | `tests/integrations/test_workbuddy_mcp.py` | 迁移 3 项 MCP 与安装器回归测试 |
| `tests/test_teacher_experience.py` | `tests/skills/test_chatduino_experience.py` | 保留 5 项教师体验意图，改为 ChatDuino 的文字接线和创作伙伴契约 |
| `assets/examples/*` | `examples/chatduino/nano/*` | 迁移 6 个 v1.2 示例并重新真实编译 |
| `references/*.md` | `skills/chatduino/references/nano-*.md` 与数据包 | 只迁移 Nano 专属事实和已核库名，避免把大资料表全部塞进 SKILL.md |
| `SKILL.md` | `skills/chatduino/SKILL.md` | 不覆盖现有 ChatDuino；迁移低自由度硬件规则和按需参考入口 |

## 原有行为基线

- Mind+ 1.x FQBN 为 `arduino:avr:nano:cpu=atmega328`。
- Mind+ 2.x FQBN 为 `mindplus:avr:nano:cpu=atmega328`。
- 发现已有 1.x 或 2.x 后直接复用，二者都可用时优先选择 2.x。
- 默认发现根目录数量受限，不扫描所有盘符。
- 排除蓝牙串口；仅有一个高置信度 Nano 时自动选择；多个候选要求用户选择。
- A6、A7 只能作为模拟输入；PWM、D0、D1 和重复引脚冲突需要提前报错。
- 编译失败最多建议自动修复两次，编译失败时不进入烧录。
- 烧录先尝试 57600，仅遇到典型同步失败时尝试 115200；端口占用等其他错误不切换 Bootloader。
- 未接有线 Nano 时停在 `awaiting-hardware`，不能把编译成功写成烧录成功。
- 6 个原示例曾用 Mind+ 2.x 真实编译；本次迁移必须在 ChatMaker 路径重新编译后才能继承当前证据。
- 旧任务未完成实体 Nano 烧录和断电重启验收，这两项仍为未验证。

## 本阶段验收

1. 原 33 项测试的行为在 ChatMaker 中保留并通过。
2. ChatMaker 新旧全部测试同时通过。
3. 本机 doctor 能发现 Mind+ 1.x 和 2.x，并选择可用环境。
4. 六个迁移示例从 ChatMaker 路径真实编译成功。
5. 无有线 Nano 时安全停在等待硬件，不执行烧录。
6. ChatDuino 默认只给文字接线块，不生成 SVG。
7. 编译、烧录、串口和实物效果继续分别报告。
