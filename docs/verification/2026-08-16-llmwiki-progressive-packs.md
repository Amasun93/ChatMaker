# LLMWiki 渐进知识包与最小 Core 验证

日期：2026-08-16

## 本次交付

- 最小 Core：`ChatMaker-Core-0.1.0-rc5.zip`
- 字节数：`206440`
- SHA-256：`e5203e0dd84dd0f7aa500706835940fdce2e9a1fbb67af1a646dfd0fd248edb9`
- 文件数：113
- 注册表：sequence `1`，生成时间 `2026-08-16T00:00:00Z`，过期时间 `2027-08-16T00:00:00Z`
- 签名 key ID：`chatmaker-official-2026-01`
- 公开锚指纹：`70570b179cf452abcc7486f76a408a25faee3702433663e99b7418498d725f67`

同一源码连续构建两次，两份 ZIP 的字节数和 SHA-256 完全一致。Core 内包含 Python 运行层、三个 Skill、全部 schema、3/12/14 条 canonical 记录、三个紧凑索引、当前案例、最小用户文档（`README.md`、`README_EN.md`、`docs/installation.md`）、Python 元数据和许可证。解压检查确认没有 `tests/`、`knowledge_sources/`、`distribution/`、`.cmpack`、详细 LLMWiki `.md` 正文、架构/API/治理/贡献者/演示文档、`CONTRIBUTING.md` 或 `RELEASE_NOTES.md`。`tests/release/test_release_package.py` 对根文件和 `docs/` 文件做精确集合断言，新增文件不能静默扩入 Core。

## 生产注册表与包

三个包在 Git 历史中都首次且仅由提交 `25ad1df2376872e81b3fe1025420cf3f76376719` 加入；该提交与 Task 7 HEAD 的三个 blob ID 相同。因此注册表使用这个不可变 commit，而不是 `main`。

| pack | bytes | SHA-256 | 不可变 URL |
| --- | ---: | --- | --- |
| `chatmaker-board-arduino-nano-classic-wiki-1.0.0.cmpack` | 10463 | `f436a6c149b9d9627f34257400854be138143d34cf928e6547a33c4366bde30a` | `https://raw.githubusercontent.com/Amasun93/ChatMaker/25ad1df2376872e81b3fe1025420cf3f76376719/distribution/packs/chatmaker-board-arduino-nano-classic-wiki-1.0.0.cmpack` |
| `chatmaker-board-arduino-uno-r3-wiki-1.0.0.cmpack` | 10291 | `67110bf2e13d5ba7a9cc00235897c135ed3ee80208991d303b19330d2250a2c6` | `https://raw.githubusercontent.com/Amasun93/ChatMaker/25ad1df2376872e81b3fe1025420cf3f76376719/distribution/packs/chatmaker-board-arduino-uno-r3-wiki-1.0.0.cmpack` |
| `chatmaker-board-esp32-devkit-v1-wiki-1.0.0.cmpack` | 10471 | `9cbf789ecf0598c24c9a5a238e7842366d2834c01f53887be338c8224579b34d` | `https://raw.githubusercontent.com/Amasun93/ChatMaker/25ad1df2376872e81b3fe1025420cf3f76376719/distribution/packs/chatmaker-board-esp32-devkit-v1-wiki-1.0.0.cmpack` |

外部生产私钥存在。签名只通过 `scripts/sign_registry.py` 完成；工具先核对派生公钥与仓库锚，再对 `registry.json` 原始字节签名。私钥内容没有写入日志、仓库、Core 或报告。提交内 detached signature 已由运行时验证器按固定锚、sequence、有效期和 schema 成功验证。

## 全新解压与用户目录

可从 HEAD 直接运行的提交内验收入口是：

```powershell
python -m unittest discover -s tests/release -p "test_clean_core_integration.py" -v
```

`tests/release/test_clean_core_integration.py` 每次创建新的解压目录、Python 3.11 venv、HOME 和 USERPROFILE。为避免联网和重复下载依赖，venv 明确复用执行测试的 Python 已安装依赖，Core 使用 setuptools `develop --no-deps` 从解压目录安装；测试同时设置 `PIP_NO_INDEX=1`、清除 `PYTHONPATH`，并把临时目录、host 配置和 ChatMaker state 全部限制在测试临时根下。

- 从 `<extracted-core>` 安装成功，导入路径来自解压 Core。
- 18 个 `chatmaker-*` 命令入口可见；catalog、route、LLMWiki index、doctor 和 WorkBuddy stdio ping 实际执行成功。
- doctor 报告 3 块板卡、12 种元器件、14 个配方、3 个紧凑索引，三个 Skill 均通过。
- Codex 临时 home 安装得到 `chatmaker/chatduino/chatweb`，doctor 成功，uninstall 后三者移除；WorkBuddy 临时配置也完成 install/doctor/uninstall，并恢复原有无关 MCP 与 host 字段。
- 安装器明确报告 `content_manager=chatmaker-pack`、`knowledge_packs_installed=[]`；知识包没有被 host installer 预装。

同一提交内验收由 `tests/release/clean_core_probe.py` 在该 venv 中执行。局部签名注册表 fixture 使用临时测试密钥和内存 transport，不使用生产私钥。第一次读取 Nano `identify-and-safety` 依次读取 registry、signature、pack 共 3 次并返回 `provenance.kind=official_pack`；第二次读取没有新增 transport 调用；换成拒绝所有网络的 transport 后，已安装的精确版本仍可离线读取。

## 自动测试

- `python -m unittest discover -s tests -v`：326 项通过，1 项跳过。跳过项是当前 Windows 账户没有创建目录符号链接权限的安全测试；同组其他路径/重解析点安全测试通过。
- release 聚焦测试：10 项通过，其中包含上述 clean-Core 集成验收。
- installer 聚焦测试：70 项通过，1 项按上面原因跳过。
- WorkBuddy integration：15 项通过。
- LLMWiki 文档与 schema 合同：17 项通过。
- 生产 registry 签名、三个 commit-pinned URL 字符串、当前本地 artifact 长度和 SHA-256 均由自动测试核对。

Codex/WorkBuddy 既有备份、重复安装拒绝、失败回滚、卸载恢复和无关 MCP/host settings 保留测试继续通过。内容管理只由 `chatmaker-pack` 提供，没有在 host installer 中增加重复动作。

## 公开可用性与证据边界

Task 7 没有 push，也没有创建 GitHub Release。2026-08-16 在推送前对三个不可变 Raw URL 做只读 GET，GitHub 均返回 404；原因是包含 artifact 的本地提交 `25ad1df…` 尚未进入公开仓库。Task 8 必须在安全合并并推送 `main` 后重新核对三个 URL 的 HTTP 200、长度和 SHA-256，再用生产 registry 做全新用户目录的公开自动下载证明。

本记录只证明软件、分发格式、签名、隔离安装和本地 fixture。它不证明公开 GitHub 下载已可用，也不证明任何板卡烧录、串口、SoftAP、HTTP、断电重启或物理效果。
