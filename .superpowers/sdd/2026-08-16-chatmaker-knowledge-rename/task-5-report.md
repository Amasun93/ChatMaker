# Task 5 Report: Safely migrate existing user state

## 状态

完成。实现严格限定在 Task 5：新增旧 Knowledge 身份迁移、接入 `PackManager`、补充迁移测试；未清理文档、未构建或发布正式 pack，也未读取私钥。

当前 HEAD 的 production pack IDs 为：

- `chatmaker-board-arduino-nano-classic-knowledge`
- `chatmaker-board-arduino-uno-r3-knowledge`
- `chatmaker-board-esp32-devkit-v1-knowledge`

本迁移仅停用对应的三个旧 `...-wiki` 身份。

## RED

1. 首次运行 `python -m unittest tests.installers.test_knowledge_state_migration -v`，因 `runtime.chatmaker.installers.knowledge_state_migration` 不存在而失败，确认新能力缺失。
2. 加入真实 Windows junction 备份路径逃逸测试后，当前实现未抛错，测试以 `KnowledgeStateMigrationError not raised` 失败；随后逐级验证/创建备份目录，禁止 symlink/reparse traversal。
3. 锁行为做反向变异验证：临时移除 `exclusive_file_lock` 后，`test_migration_waits_for_the_pack_manager_lock` 以 `TimeoutError not raised` 失败；恢复锁后通过。

## GREEN

- 聚焦迁移测试：`python -m unittest tests.installers.test_knowledge_state_migration -v`，7/7 通过。
- PackManager 回归：`python -m unittest tests.installers.test_pack_manager -v`，50 项通过，1 项既有普通 symlink 测试因本机 Windows symlink 权限跳过；本任务新增的 junction 安全测试实际执行并通过。

## 实现与安全边界

- `migrate_legacy_knowledge_state(paths)` 使用与 `PackManager` 相同的 manager lock，并有进程内线程锁保护。
- 仅从 `active.json` 与 `installed-packs.json` 的 `packs` metadata 删除精确旧 ID；保留当前 ID 和未知 ID，绝不把旧 ID/目录改写成新 production pack。
- `active.json` 确实停用旧身份时 generation 加一。
- 替换前将所有已存在的目标 state files 原始字节写入唯一备份目录；完成后写入幂等 marker。
- 替换前故障注入会保留 `active.json` 与 `installed-packs.json` 原字节；替换过程异常会按原字节回滚已替换文件。
- cache（含 receipt）、legacy store、overrides 不移动、不改名、不删除；`MigrationResult.preserved_paths` 返回保留位置。
- 备份根的 symlink/reparse point 会在任何外部写入前被拒绝。
- `PackManager` 在当前 allowlist 校验读取旧 state 前 lazy 执行一次迁移。

## 文件

- 新增 `runtime/chatmaker/installers/knowledge_state_migration.py`
- 修改 `runtime/chatmaker/installers/pack_manager.py`
- 新增 `tests/installers/test_knowledge_state_migration.py`
- 新增本报告 `task-5-report.md`

## 提交

- `feat: migrate prior knowledge pack state safely`（本报告与实现同一提交）

## 自检

- [x] 只在指定 worktree 工作。
- [x] 旧/新 pack IDs 以当前 HEAD 代码和改名提交为准。
- [x] 使用真实临时 user state root，覆盖 active、installed metadata、cache receipt、store、overrides。
- [x] RED 在实现前出现，并额外完成路径逃逸 RED 与锁反向变异 RED。
- [x] 加锁、幂等、字节级备份、精确停用、数据保留、marker 均有实现或测试证据。
- [x] 替换前故障注入证明两份原 state bytes 不变。
- [x] 未把旧数据当作新包，未删除 cache/store/overrides。
- [x] 未读取私钥，未做 Task 5 以外的文档清理或正式发布。

## 关注点

- 备份与失败尝试留下的备份目录会有意保留，不自动清理；这是避免无提示删除和保留恢复证据的取舍。
- PackManager 原回归中一个普通 symlink 用例因 Windows 权限跳过；本任务自己的 Windows junction 逃逸用例无需该权限，已实际通过。
