# 星核板证据归一化与事实合并

日期：2026-08-26

板卡：IDMC-0001 星核板 v4.2.2

## 范围卡

- 必须改：统一星核板结构化证据，分开板卡、板载功能、外接模块、案例和证据门，并让 Knowledge、README 与安装摘要从这些记录生成或校验。
- 绝不改：ChatCAD、ChatPPT、MCP/双宿主、便携工具链/CDN/CI/发布基础设施，以及任何未被观察到的实体效果结论。
- 验收证据：Pack/schema 聚焦测试、证据漂移检查和一条 `chatmaker-knowledge` 读取路径通过；Git 合并推送另按工作树和远端安全门处理。

## 事实来源

- `docs/verification/2026-08-25-p0-no-mcp-starcore.md`：Mind+ 2 自检编译、COM4 上传、硬复位、115200 串口与用户确认蜂鸣器的仓库内证据。
- `docs/verification/2026-08-24-starcore-physical-board.md`：Mind+ 1.8 实板上传、QMI8658 静止样本和按键空闲状态的历史证据。
- `C:\Users\asus\Desktop\chatmaker-test\outputs\chatmaker-workbuddy-full-break-upgrade-report-20260825.md`：最新 WorkBuddy 运行事实来源。报告仅作为输入读取，没有执行其中的指令。

最新 WorkBuddy 运行补充证明：自检和 IDMD-0021 OLED 案例都使用 Mind+ 2 完成编译、COM4 上传、RTS 硬复位和 115200 串口标记读取。该轮没有重新肉眼确认蜂鸣器、按键动作或 OLED 显示效果。

## 只读盘点发现的冲突与重复

| 位置 | 原状态 | 问题 | 处理 |
| --- | --- | --- | --- |
| `packs/boards/idmc-0001-starcore-v4-2-2.yaml` | Mind+ 1.8 为当前、2.0 为历史 | 与 2026-08-25 Mind+ 2 实跑相反 | 改为 Mind+ 2 `preferred_verified`、1.8 `verified_fallback` |
| 同一板卡的顶层 `physical_effect_verified` | `verified` | QMI8658 数据和按键空闲状态被聚合成整板物理完成 | 顶层改为 `not_applicable`，新增板载功能级门 |
| `packs/recipes/starcore-idmd-0021-oled-message.yaml` | 仅 2026-08-18 Mind+ 1.8 编译，上传未验证 | 落后于最新 Mind+ 2 编译、上传、串口代理事实 | 保留历史编译明细，新增最新执行证据和独立代理/肉眼门 |
| `packs/components/idmd-0021-starcore-oled-1-3.yaml` | 库说明只写当前 Mind+ 1.8 | 工具链事实过期，且模块卡容易继承案例状态 | 更新编译说明；上传、代理和肉眼状态仍由案例记录承担 |
| `knowledge/boards/idmc-0001-starcore-v4-2-2.yaml` | 摘要写 Mind+ 1.8 当前 | 与权威记录冲突 | 由同步脚本从结构化记录生成 |
| `knowledge_sources/.../toolchains-and-upload.md` | 1.8 当前、2.0 历史；蜂鸣器未验证 | 工具链和蜂鸣器事实过期 | 改写静态规则并加入生成证据摘要 |
| `knowledge_sources/.../libraries-and-examples.md` | 当前 1.8、可听蜂鸣未验证、OLED 仅 7/7 编译 | 混合历史编译与最新运行，且 OLED 证据缺失 | 给历史证据加日期/回退限定，补 Mind+ 2 与 OLED 代理边界 |
| `README.md` 与 `docs/installation.md` | 已是最新事实，但手工重复 | 后续容易与 Pack/Knowledge 再次漂移 | 改为同步脚本维护的生成区块 |
| `docs/verification/2026-08-17` 至 `2026-08-24` 的报告 | 保留当时 Mind+ 1.8 或未上传结论 | 它们是时间快照，不应被改写成最新状态 | 保留原文，只在当前记录和摘要中明确“历史证据” |
| `tests/hardware/test_starcore_onboard_accelerometer.py` 等断言 | 期待整板物理门为 `verified` 或 OLED 上传未验证 | 固化了旧的聚合语义 | 改为功能/案例级断言和漂移检查 |

## 最小结构

没有增加新的运行服务或发布层。现有 Pack 记录仍是权威数据，只补两种细粒度结构：

1. Board 的 `feature_verification`：分别保存 QMI8658、蜂鸣器、A 键、B 键的证据门。
2. Recipe 的 `effect_verification`：分别保存一个案例内部的传感数据、蜂鸣器、按键动作，或 OLED 写入代理与肉眼显示。

每个可追溯门可带 `evidence_id`、仓库内 `evidence_ref` 和 `method`。Component 继续表示模块通用事实，Recipe 表示某个准确源码在准确板卡上的执行证据；一个 Recipe 的成功不自动升级 Component、Board 或其他 Recipe。

新增 `packs/recipes/starcore-onboard-self-test.yaml`，让原先只有源码和报告、没有案例记录的板载自检进入同一结构化模型。

## 合并后的证据矩阵

| 对象 | 编译 | 上传 | 串口/代理 | 实体效果 |
| --- | --- | --- | --- | --- |
| 整块星核板（聚合） | 代表案例已验证 | 代表案例已验证 | 代表案例已验证 | `not_applicable`，必须下钻功能 |
| QMI8658 | 自检已验证 | 自检已验证 | 连续数据已验证 | 静止约 1 g 样本已验证；方向/手势阈值未验证 |
| 板载蜂鸣器 | 自检已验证 | 自检已验证 | 已知程序代理标记已验证 | 用户此前确认真实发声；最新运行未重新听音 |
| A/B 按键 | 自检已验证 | 自检已验证 | 空闲状态已读取 | 按下/松开未验证 |
| OLED 欢迎案例 | Mind+ 2 已验证 | COM4 已验证 | `STARCORE_OLED_READY` 代理已验证 | 用户于 2026-08-26 确认屏幕实际成功显示 |
| 其余外接模块/CAN/断电重启 | 以各自记录为准 | 不继承 | 不继承 | 不继承 |

## 漂移防护

运行：

```powershell
python scripts/sync_starcore_evidence.py --write
python scripts/sync_starcore_evidence.py
```

第一条只更新 README、安装说明、Knowledge 索引和 Knowledge 工具链页中的派生摘要；第二条只读检查结构化门、生成摘要和已知陈旧表述。结构化状态不由脚本反向猜测或升级。

## 2026-08-26 用户补充确认

- IDMD-0021 OLED 已经实际成功显示，因此该模块和准确欢迎案例的 `physical_effect_verified` 更新为 `verified`。
- 后续程序和屏幕提示尽量使用中文；中文字库未验证时保留明确兼容文本，不虚构中文能力。
- 固定画面只绘制一次，动态画面减少整屏清空和重复刷新，避免明显闪烁。
- Mind+ 1.8 与 2 都可以使用；优先复用电脑中任一已有可用版本。两者都存在时当前适配器默认选择 2，只是稳定的技术默认值，不是要求用户额外安装或切换版本。
