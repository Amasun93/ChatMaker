# ChatCAD 3D 接单与交付分流设计

## 目标

让零基础用户在三维需求尚未讨论清楚时保持在对话阶段，避免 ChatCAD 过早生成模型、预览和截图。该规则适用于所有 ChatCAD 3D 任务，课堂参数化建模是典型场景，不是单独模式。

## 默认流程

1. ChatCAD 先确认造型、关键尺寸、需要调整的参数和使用场景。
2. ChatCAD 用简短任务卡复述已确认内容；用户确认前不得调用 `cad_generate`。
3. 用户明确说“开始生成”后，ChatCAD 再询问交付路线：
   - MakerLab（默认推荐）：直接给完整 OpenSCAD 代码、MakerLab 官方入口和简短粘贴说明。
   - ChatMaker 预览：仅在用户不使用 MakerLab 时交付右侧 3D 参数预览。

MakerLab 路线使用轻量 `makerlab-code` 交付模式，只返回 `scad_code`，不创建 `.scad` 文件、STL、右侧预览、渲染图或截图。只有 `chatmaker-preview` 模式才写出完整模型和预览文件。

## 边界

本次只修改 ChatCAD 专项规则、ChatMaker 路由边界和 WorkBuddy MCP 初始化指令，不重写几何生成器，不改变 Chat2D，不增加安装器或发布链改造。

## 验收

- MCP 初始化指令明确包含任务卡、显式“开始生成”门槛和 `cad_generate` 禁止条件。
- MakerLab 被设为默认推荐，并要求直接展示 OpenSCAD 代码。
- MakerLab 代码模式不创建输出目录或辅助文件，`model_generated` 保持 `unverified`。
- STL、右侧预览和截图不是 MakerLab 路线的默认交付。
- 只有不使用 MakerLab 时才交付 ChatMaker 右侧预览。
