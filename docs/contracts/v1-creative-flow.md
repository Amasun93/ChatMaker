# ChatMaker V1.0 创作流程合同

## 一句话目标

用户通过 AI 对话表达想法，ChatMaker 先帮助他找到一个值得做、能够观察结果的最小作品，再逐步完成硬件、可选网页和可选制造结构。

## 对话流程

```text
想法不清楚 → 每轮讨论 1–2 个真正影响作品的问题
想法已清楚 → 直接设计最小可运行版本
硬件已运行 → 询问是否增加传感器、显示屏或网页交互
作品已确认 → 询问是否需要激光切割盒子或 3D 打印外壳
```

网页和 CAD 都是按需分支，不是每个项目的必经步骤。用户可以在任何阶段结束，ChatMaker 只推荐最自然的下一步，不一次展示全部功能。

## V1.0 板卡和环境边界

- 正式主线：Arduino Nano Classic、Arduino Uno R3、Starcore v4.2.2。
- Nano、Uno 允许发现并复用 Mind+ 1.x/2.x；用户不需要进入 Mind+ 手动开发。
- ESP32 DevKit V1 的既有能力继续保留，但不阻塞 V1.0。
- 缺少环境、程序库或硬件时，必须返回当前可继续做什么，不能把等待状态写成失败或成功。

## 专业模块

- ChatMaker：唯一面向用户的入口，理解作品目标并在内部调用专业模块。
- ChatDuino：板卡、模块、接线、代码、编译、烧录、串口和实物确认。
- ChatWeb：独立课堂工具，或用户明确需要后的硬件网页交互。
- ChatCAD：制造入口；Chat2D 面向激光切割，Chat3D 面向 3D 打印。
- ChatMaker Knowledge：共享板卡、模块、库、示例、机械和设备工艺事实。

ChatDuino、ChatWeb 和 ChatCAD 保持独立目录，便于分别维护和测试，但不作为用户安装后的独立入口。它们只读取 ChatMaker 仓库内的规范数据和运行工具，不在运行时查询旧 Nano、旧星核板或其他外部 Skill。

## 完成证据

以下状态必须分别记录：

1. `environment_ready`
2. `source_generated`
3. `code_compiled`
4. `firmware_uploaded` 或 `page_served`
5. `serial_or_browser_observed`
6. `physical_effect_verified`

一个较早状态不能自动证明后续状态。没有实体板时，可以完成生成和编译，但烧录、重启、串口、网页真实交换和实物效果保持 `unverified`。

## V1.0 代表验收

1. Nano + 传感器 + OLED。
2. Uno + 传感器/显示屏或执行器。
3. 星核板 + 传感器，并按需增加一个真实网页交互。
4. Chat2D 激光切割盒子：可编辑、分层导出并查看拼装预览。
5. Chat3D 打印外壳：可调整、可旋转并导出 OpenSCAD/STL。
