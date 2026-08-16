# LLMWiki 渐进知识包与最小 Core 验证

日期：2026-08-16

## 本次交付

- 最小 Core：`ChatMaker-Core-0.1.0-rc5.zip`
- 字节数：`216863`
- SHA-256：`56f714354cd92b83582b3b72d4d284c83be7111c80968de46641b413fd6059f5`
- 文件数：115
- 注册表：sequence `1`，生成时间 `2026-08-16T00:00:00Z`，过期时间 `2026-09-15T00:00:00Z`
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

- bootstrap 提交 A `b46aad2e8ec5f956a2f73cf974851e209f556c89` 上运行 `python -m unittest discover -s tests`：共 371 项，370 项通过，1 项跳过，耗时 153.445 秒。跳过项是当前 Windows 账户没有创建目录符号链接权限的安全测试；同组真实 junction、重解析点、祖先目录替换、路径与硬链接安全测试通过。
- Playwright Chromium：4 项通过，覆盖课堂页、模拟硬件页、ESP32 AP 模拟页和高级游乐场。
- release package 聚焦测试：10 项通过；上述 clean-Core 集成验收另有 1 项通过，耗时 40.596 秒。
- canonical pack validation：18 项通过；LLMWiki 内容与确定性构建聚焦验证：5 项通过。
- 项目内 ChatMaker、ChatDuino、ChatWeb Skill 校验全部通过，三个 Skill 又分别通过 Codex 系统 `quick_validate.py`。
- doctor 报告 3 块板卡、12 类元器件、14 个案例、3 个 LLMWiki 索引和 29 个 verification snapshot，错误为 0；知识发布治理报告 3 个 manifests、24 个 pages、错误为 0。
- WorkBuddy stdio `initialize` / `tools/list` 实际返回版本 `1.8.0`、24 个唯一工具，并包含 `llmwiki_get`。
- 同一源码独立构建两次 Core，两份均为 216863 字节、115 个文件且 SHA-256 都是 `56f714354cd92b83582b3b72d4d284c83be7111c80968de46641b413fd6059f5`。
- 生产 registry 签名、三个 commit-pinned URL、当前 artifact 长度和 SHA-256 均由自动测试与公网只读验证共同核对。

Codex/WorkBuddy 既有备份、重复安装拒绝、失败回滚、卸载恢复和无关 MCP/host settings 保留测试继续通过。内容管理只由 `chatmaker-pack` 提供，没有在 host installer 中增加重复动作。

## 公开可用性与证据边界

2026-08-16 将经过本地完整验证的 bootstrap 提交 A `b46aad2e8ec5f956a2f73cf974851e209f556c89` 推送到 `main` 后，`git ls-remote origin refs/heads/main` 返回完全相同的提交。随后完成以下公网只读证明：

- 正式 registry URL 返回 HTTP 200、2147 字节、SHA-256 `c9eba3650ceb0c1bfe9dc364b36c1c2671796b2ba81c9150914baceab947dfdb`。
- detached signature URL 返回 HTTP 200、165 字节、SHA-256 `7d760766bdcf5fa0911cf645b45776648671269b9370c2233f6fdac1b28d31f5`；运行时使用固定公钥 `chatmaker-official-2026-01` 验证通过，registry sequence 为 `1`。
- 三个 commit-pinned `.cmpack` URL 全部返回 HTTP 200，实际长度和 SHA-256 与上表及已签名 registry 完全一致。
- 在全新临时用户目录中，用实际 `UrlTransport`、`PackManager`、正式 trust anchor 和 GitHub registry 请求 Nano 的 `identify-and-safety`。第一次成功并恰好产生 3 次网络调用（registry、signature、Nano pack），返回 `official_pack` provenance、版本 `1.0.0`、正文 429 字节。
- 同一请求第二次成功，累计网络调用仍为 3，即新增下载 0 次。随后换成任何 `fetch` / `fetch_to` 都会失败的新离线 transport 和新 `PackManager`，继续从同一用户目录读取成功，离线网络调用为 0；active generation 为 1，激活与缓存归档哈希均为 Nano 包哈希 `f436a6c…`。

本任务没有创建 GitHub Release；公开分发通过仓库 `main` 上的签名 registry 和不可变 commit URL 完成。本记录证明软件、分发格式、签名、自动按需安装、缓存与离线读取；它不证明任何板卡烧录、串口、SoftAP、HTTP、断电重启、机械尺寸或物理效果。当前也没有实现 ChatCAD、DXF、STL 或 3D 生成。
