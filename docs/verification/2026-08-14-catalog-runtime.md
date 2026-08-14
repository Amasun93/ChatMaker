# ChatMaker 资料目录运行层验收

## 目的

让 ChatDuino 在安装到 Codex 或 WorkBuddy 后，能够真正搜索和读取 `packs` 中的板卡、模块和项目资料，而不是只在 Skill 文字里声明“读取资料库”。

## 入口

```text
WorkBuddy
catalog_search
catalog_get

Codex
chatmaker-catalog --request-json ...
```

`catalog_search` 支持 `board`、`component`、`recipe` 三种资料，并匹配稳定 ID、英文名称、中文别名、类别、接口和关联板卡。`catalog_get` 返回完整 YAML 记录，包括识别方法、供电范围、引脚、限制、库、示例、常见故障和四层证据状态。

## 已验证案例

```text
搜索“继电器”
→ one-channel-relay-module-5v

搜索“电位器”
→ linear-potentiometer-10k

读取 ws2812b-addressable-rgb
→ source_reviewed: verified
→ code_compiled: verified
→ firmware_uploaded: unverified
→ physical_effect_verified: unverified
```

WorkBuddy 的 MCP 工具总数由 11 个增加到 13 个。目录查询不会把编译成功升级成烧录或实物成功。
