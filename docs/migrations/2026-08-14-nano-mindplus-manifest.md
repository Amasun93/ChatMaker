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

审计时原检出保持只读，并补记以下证据：

- `HEAD = 9ebc6bff16529557aa2cebe661755cf6c51d79ed`
- `git status --short` 返回空结果，状态为 clean
- 本轮迁移审计未对原检出执行任何 source write

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
| `assets/examples/*` | `examples/chatduino/nano/*` | 迁移 6 个 v1.2 示例，并在 ChatMaker 当前路径扩展为 10 个 compile-verified 示例 |
| `references/*.md` | `skills/chatduino/references/nano-*.md` 与数据包 | 只迁移 Nano 专属事实和已核库名，避免把大资料表全部塞进 SKILL.md |
| `SKILL.md` | `skills/chatduino/SKILL.md` | 不覆盖现有 ChatDuino；迁移低自由度硬件规则和按需参考入口 |

## 33 项旧测试一对一映射

### 25 项 Nano 运行层测试

| 旧测试 | ChatMaker 目标测试 |
| --- | --- |
| `tests/test_nano_bridge.py::NanoBridgeContractTests::test_existing_v2_is_used_without_install_recommendation` | `tests/hardware/test_nano_mindplus.py::NanoBridgeContractTests::test_existing_v2_is_used_without_install_recommendation` |
| `tests/test_nano_bridge.py::NanoBridgeContractTests::test_default_discovery_does_not_probe_every_possible_drive` | `tests/hardware/test_nano_mindplus.py::NanoBridgeContractTests::test_default_discovery_does_not_probe_every_possible_drive` |
| `tests/test_nano_bridge.py::NanoBridgeContractTests::test_registry_install_location_is_accepted_without_drive_scan` | `tests/hardware/test_nano_mindplus.py::NanoBridgeContractTests::test_registry_install_location_is_accepted_without_drive_scan` |
| `tests/test_nano_bridge.py::NanoBridgeContractTests::test_existing_v1_is_used_without_install_recommendation` | `tests/hardware/test_nano_mindplus.py::NanoBridgeContractTests::test_existing_v1_is_used_without_install_recommendation` |
| `tests/test_nano_bridge.py::NanoBridgeContractTests::test_no_install_prefers_official_v1_for_windows_x64` | `tests/hardware/test_nano_mindplus.py::NanoBridgeContractTests::test_no_install_prefers_official_v1_for_windows_x64` |
| `tests/test_nano_bridge.py::NanoBridgeContractTests::test_windows_arm_does_not_download_unconfirmed_v1_binary` | `tests/hardware/test_nano_mindplus.py::NanoBridgeContractTests::test_windows_arm_does_not_download_unconfirmed_v1_binary` |
| `tests/test_nano_bridge.py::NanoBridgeContractTests::test_linux_routes_by_distribution_and_architecture` | `tests/hardware/test_nano_mindplus.py::NanoBridgeContractTests::test_linux_routes_by_distribution_and_architecture` |
| `tests/test_nano_bridge.py::NanoBridgeContractTests::test_port_selection_prefers_one_likely_nano_and_rejects_bluetooth` | `tests/hardware/test_nano_mindplus.py::NanoBridgeContractTests::test_port_selection_prefers_one_likely_nano_and_rejects_bluetooth` |
| `tests/test_nano_bridge.py::NanoBridgeContractTests::test_multiple_unknown_wired_ports_require_selection` | `tests/hardware/test_nano_mindplus.py::NanoBridgeContractTests::test_multiple_unknown_wired_ports_require_selection` |
| `tests/test_nano_bridge.py::NanoBridgeContractTests::test_v1_and_v2_use_distinct_nano_fqbn` | `tests/hardware/test_nano_mindplus.py::NanoBridgeContractTests::test_v1_and_v2_use_distinct_nano_fqbn` |
| `tests/test_nano_bridge.py::NanoBridgeContractTests::test_pin_validator_rejects_nano_only_constraints` | `tests/hardware/test_nano_mindplus.py::NanoBridgeContractTests::test_pin_validator_rejects_nano_only_constraints` |
| `tests/test_nano_bridge.py::NanoBridgeContractTests::test_prepare_code_creates_valid_arduino_sketch` | `tests/hardware/test_nano_mindplus.py::NanoBridgeContractTests::test_prepare_code_creates_valid_arduino_sketch` |
| `tests/test_nano_bridge.py::NanoBridgeContractTests::test_v2_compile_command_uses_mindplus_nano_and_config` | `tests/hardware/test_nano_mindplus.py::NanoBridgeContractTests::test_v2_compile_command_uses_mindplus_nano_and_config` |
| `tests/test_nano_bridge.py::NanoBridgeContractTests::test_v1_compile_command_uses_arduino_nano_fqbn` | `tests/hardware/test_nano_mindplus.py::NanoBridgeContractTests::test_v1_compile_command_uses_arduino_nano_fqbn` |
| `tests/test_nano_bridge.py::NanoBridgeContractTests::test_upload_does_not_fallback_bootloader_on_unrelated_error` | `tests/hardware/test_nano_mindplus.py::NanoBridgeContractTests::test_upload_does_not_fallback_bootloader_on_unrelated_error` |
| `tests/test_nano_bridge.py::NanoBridgeContractTests::test_upload_tries_115200_only_after_sync_failure_at_57600` | `tests/hardware/test_nano_mindplus.py::NanoBridgeContractTests::test_upload_tries_115200_only_after_sync_failure_at_57600` |
| `tests/test_nano_bridge.py::NanoBridgeContractTests::test_compile_upload_stops_before_upload_when_compile_fails` | `tests/hardware/test_nano_mindplus.py::NanoBridgeContractTests::test_compile_upload_stops_before_upload_when_compile_fails` |
| `tests/test_nano_bridge.py::NanoBridgeContractTests::test_compile_upload_automatically_uploads_after_compile` | `tests/hardware/test_nano_mindplus.py::NanoBridgeContractTests::test_compile_upload_automatically_uploads_after_compile` |
| `tests/test_nano_bridge.py::NanoBridgeContractTests::test_compile_upload_prompts_for_connection_when_hardware_is_missing` | `tests/hardware/test_nano_mindplus.py::NanoBridgeContractTests::test_compile_upload_prompts_for_connection_when_hardware_is_missing` |
| `tests/test_nano_bridge.py::NanoBridgeContractTests::test_compile_failure_is_marked_for_bounded_code_repair` | `tests/hardware/test_nano_mindplus.py::NanoBridgeContractTests::test_compile_failure_is_marked_for_bounded_code_repair` |
| `tests/test_nano_bridge.py::NanoBridgeContractTests::test_installer_refuses_download_when_any_mindplus_exists` | `tests/hardware/test_nano_mindplus.py::NanoBridgeContractTests::test_installer_refuses_download_when_any_mindplus_exists` |
| `tests/test_nano_bridge.py::NanoBridgeContractTests::test_installer_only_auto_downloads_allowlisted_official_url` | `tests/hardware/test_nano_mindplus.py::NanoBridgeContractTests::test_installer_only_auto_downloads_allowlisted_official_url` |
| `tests/test_nano_bridge.py::NanoBridgeContractTests::test_environment_prepare_returns_manual_route_for_unconfirmed_arch` | `tests/hardware/test_nano_mindplus.py::NanoBridgeContractTests::test_environment_prepare_returns_manual_route_for_unconfirmed_arch` |
| `tests/test_nano_bridge.py::NanoBridgeContractTests::test_installer_launch_requires_explicit_request_and_existing_file` | `tests/hardware/test_nano_mindplus.py::NanoBridgeContractTests::test_installer_launch_requires_explicit_request_and_existing_file` |
| `tests/test_nano_bridge.py::NanoBridgeContractTests::test_existing_mindplus_blocks_install_launch` | `tests/hardware/test_nano_mindplus.py::NanoBridgeContractTests::test_existing_mindplus_blocks_install_launch` |

### 3 项 WorkBuddy / 安装器测试

| 旧测试 | ChatMaker 目标测试 |
| --- | --- |
| `tests/test_workbuddy_bridge.py::WorkBuddyBridgeTests::test_server_exposes_nano_tools_only` | `tests/integrations/test_workbuddy_mcp.py::WorkBuddyBridgeTests::test_server_exposes_catalog_esp32_uno_nano_and_serial_tools_only` |
| `tests/test_workbuddy_bridge.py::WorkBuddyBridgeTests::test_installer_preserves_existing_servers` | `tests/integrations/test_workbuddy_mcp.py::WorkBuddyBridgeTests::test_installer_preserves_existing_servers` |
| `tests/test_workbuddy_bridge.py::WorkBuddyBridgeTests::test_waiting_for_hardware_is_a_prompt_not_an_mcp_tool_error` | `tests/integrations/test_workbuddy_mcp.py::WorkBuddyBridgeTests::test_waiting_for_hardware_is_a_prompt_not_an_mcp_tool_error` |

### 5 项教师体验测试

| 旧测试 | ChatMaker 目标测试 |
| --- | --- |
| `tests/test_teacher_experience.py::TeacherExperienceContractTests::test_skill_requires_two_high_visibility_code_blocks` | `tests/skills/test_chatduino_experience.py::TeacherExperienceContractTests::test_skill_requires_two_high_visibility_code_blocks` |
| `tests/test_teacher_experience.py::TeacherExperienceContractTests::test_beginner_guidance_translates_jargon_with_analogies` | `tests/skills/test_chatduino_experience.py::TeacherExperienceContractTests::test_beginner_guidance_translates_jargon_with_analogies` |
| `tests/test_teacher_experience.py::TeacherExperienceContractTests::test_photo_is_optional_and_unknown_parts_use_guided_questions` | `tests/skills/test_chatduino_experience.py::TeacherExperienceContractTests::test_photo_is_optional_and_unknown_parts_use_guided_questions` |
| `tests/test_teacher_experience.py::TeacherExperienceContractTests::test_output_contract_keeps_wiring_and_code_in_fenced_blocks` | `tests/skills/test_chatduino_experience.py::TeacherExperienceContractTests::test_output_contract_keeps_wiring_and_code_in_fenced_blocks` |
| `tests/test_teacher_experience.py::TeacherExperienceContractTests::test_skill_defaults_to_compile_and_auto_upload` | `tests/skills/test_chatduino_experience.py::TeacherExperienceContractTests::test_skill_defaults_to_compile_and_auto_upload` |

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
- 6 个原示例曾用 Mind+ 2.x 真实编译；本次迁移已在 ChatMaker 路径重新验证这 6 个原示例，并把当前 compile-verified 范围扩展到 10 个 Nano 示例。
- 旧任务未完成实体 Nano 烧录和断电重启验收，这两项仍为未验证。

## 本阶段验收

1. 原 33 项测试的行为在 ChatMaker 中保留并通过。
2. ChatMaker 新旧全部测试同时通过。
3. 本机 doctor 能发现 Mind+ 1.x 和 2.x，并选择可用环境。
4. 六个原始 v1.2 示例从 ChatMaker 路径真实编译成功，并与另外四个当前 ChatMaker Nano 示例一起构成 10 个 compile-verified 示例。
5. 无有线 Nano 时安全停在等待硬件，不执行烧录。
6. ChatDuino 默认只给文字接线块，不生成 SVG。
7. 编译、烧录、串口和实物效果继续分别报告。
