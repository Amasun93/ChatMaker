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

## Fix round 1：审查修复追加（2026-08-16）

审查提出的 6 项 Important 已逐项按 RED→GREEN 修复，范围仍只涉及 Task 5 的迁移模块、迁移测试和本报告。

### RED 证据

1. replace 后目录同步失败补偿：
   - 命令：`python -m unittest tests.installers.test_knowledge_state_migration.KnowledgeStateMigrationTests.test_directory_sync_failure_after_state_replace_restores_original_bytes tests.installers.test_knowledge_state_migration.KnowledgeStateMigrationTests.test_marker_sync_failure_removes_marker_and_restores_original_state -v`
   - 初始输出：2 项失败；第一项显示 active 已变为 generation 8 而非原字节，第二项显示 marker 仍存在。
2. stale/preseeded marker：
   - 命令：`python -m unittest tests.installers.test_knowledge_state_migration.KnowledgeStateMigrationTests.test_stale_marker_with_restored_legacy_state_is_not_trusted tests.installers.test_knowledge_state_migration.KnowledgeStateMigrationTests.test_preseeded_marker_with_missing_backup_cannot_skip_migration -v`
   - 初始输出：2 项失败，均错误返回 `changed=False`。
3. Windows marker path 与 canonical containment：
   - 命令：`python -m unittest tests.installers.test_knowledge_state_migration.KnowledgeStateMigrationTests.test_marker_paths_reject_windows_separators_drives_and_unc tests.installers.test_knowledge_state_migration.KnowledgeStateMigrationTests.test_marker_backup_cannot_escape_root_through_intermediate_junction -v`
   - 初始输出：反斜杠父跳转未抛错；中间 junction 指向 root 外 backup 时仍返回该 backup。
4. 恶意 `PackPaths`：
   - 命令：`python -m unittest tests.installers.test_knowledge_state_migration.KnowledgeStateMigrationTests.test_malicious_pack_paths_are_rejected_before_lock_or_backup_write -v`
   - 初始输出：迁移已在 root 外创建 backup 后才以 `ValueError` 崩溃，证明校验发生过晚。
5. 目录 TOCTOU：
   - 命令：`python -m unittest tests.installers.test_knowledge_state_migration.KnowledgeStateMigrationTests.test_backup_directory_is_guarded_against_in_place_junction_swap -v`
   - 初始输出：`attempted=False`，不存在任何受保护的首个 backup 写入边界。
6. Windows 目录持久化：
   - 命令：`python -m unittest tests.installers.test_knowledge_state_migration.KnowledgeStateMigrationTests.test_windows_directory_sync_invokes_flush_file_buffers_adapter -v`
   - 初始输出：`TypeError: _fsync_directory() got an unexpected keyword argument 'windows_flusher'`，且原实现直接返回。

### 修复结果

- atomic write 在 replace 成功的下一语句即记录补偿责任；state directory fsync 失败会恢复原字节，marker directory fsync 失败会先移除 marker 再恢复 state。
- 先读取当前 state，再接受 marker；仅当当前旧 ID 已不存在、marker 结构合法、UUID backup 目录存在且 backup state 确实包含全部 deactivated IDs 时才视为幂等完成。
- marker 路径拒绝反斜杠、drive/UNC、`.`/`..`，并在 `resolve(strict=False)` 后验证绝对 containment；中间 junction 不能把 backup/preserved path 带出 root。
- 在 manager lock 文件产生前，将传入 `PackPaths` 的所有 dataclass 字段与 `PackPaths.from_root(root)` 的规范绝对布局逐项比对。
- Windows 从卷根到 state/backup 持有无 reparse 的目录句柄；首个 backup 临时文件句柄在攻击回调前已打开，随后通过 `SetFileInformationByHandle(FileRenameInfo)` 原子替换。POSIX 使用 `dir_fd`、`O_NOFOLLOW` 和 descriptor-relative read/create/replace/unlink，避免 check-then-use 路径重解析。
- Windows `_fsync_directory` 复用 PackManager 等级的 `CreateFileW(...FILE_FLAG_BACKUP_SEMANTICS) + FlushFileBuffers`，并保留可注入 flusher 供断言与故障测试。

### GREEN 与回归

- `python -m unittest tests.installers.test_knowledge_state_migration -v`
  - `Ran 16 tests in 3.693s`
  - `OK`
- `python -m unittest tests.installers.test_pack_manager`
  - `Ran 50 tests in 107.791s`
  - `OK (skipped=1)`
- PackManager 的 skip 仍是既有普通 symlink 权限用例；本次新增真实 Windows junction TOCTOU 与 marker junction 用例均实际执行并通过。

### 审查修复提交

- `fix: harden knowledge state migration`（本追加报告与修复同一提交）

### Fix round 1 最终合并验证

- 命令：`python -m unittest tests.installers.test_knowledge_state_migration tests.installers.test_pack_manager -v`
- 输出：`Ran 66 tests in 141.258s`；`OK (skipped=1)`。
- 六项 finding 覆盖自检：
  1. replace/fsync 补偿：`test_directory_sync_failure_after_state_replace_restores_original_bytes`、`test_marker_sync_failure_removes_marker_and_restores_original_state`。
  2. stale/preseeded marker 与 backup 结构：`test_stale_marker_with_restored_legacy_state_is_not_trusted`、`test_preseeded_marker_with_missing_backup_cannot_skip_migration`。
  3. Windows 路径语法和 canonical containment：`test_marker_paths_reject_windows_separators_drives_and_unc`、`test_marker_backup_cannot_escape_root_through_intermediate_junction`。
  4. 全量 `PackPaths` 零写入前校验：`test_malicious_pack_paths_are_rejected_before_lock_or_backup_write`。
  5. junction/rename TOCTOU：`test_backup_directory_is_guarded_against_in_place_junction_swap`；Windows 使用 guarded handles + handle rename，POSIX 使用 `dir_fd` + `O_NOFOLLOW`。
  6. Windows directory durability：`test_windows_directory_sync_invokes_flush_file_buffers_adapter`，production 默认进入 `FlushFileBuffers` adapter。
- 关注点：唯一 skip 是 PackManager 原有普通 symlink 权限测试；本轮新增的 Windows junction、TOCTOU 和 FlushFileBuffers adapter 测试均实际执行。失败尝试和成功迁移的 backup 仍按“不无提示删除”要求保留。
