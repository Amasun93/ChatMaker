# LLMWiki 章节格式 / LLMWiki page format

LLMWiki 是给人和 AI 阅读的被动知识页。它可以解释板卡、安全、工具链、案例和通信方式，但不能复制或改写 `packs/boards`、`packs/components`、`packs/recipes` 中的规范事实。

LLMWiki pages are passive knowledge for people and AI. They may explain a board, safety, toolchains, examples, and protocols, but must not duplicate or replace canonical facts from `packs/boards`, `packs/components`, or `packs/recipes`.

## 一页一个章节 / One section per page

文件名必须与紧凑索引中的 `section_id` 相同：

```text
llmwiki/sections/<section-id>.md
```

每页使用 UTF-8、LF 换行，并以这一段 YAML front matter 开始：

```yaml
---
schema_version: "1.0"
kind: llmwiki-page
stable_id: arduino-nano-classic-identify-and-safety
board_id: arduino-nano-classic
section_id: identify-and-safety
source_refs:
  - source-arduino-nano-classic-documentation
---
```

Front matter 必须恰好包含上面的六个字段，不能增加 `title`、`source_manifest` 或其他平行身份字段。正文必须非空且完整；65,536 字节上限只计算结束分隔线之后的 UTF-8 正文字节，不计算 front matter。v1 不分页；不要把安全警告或代码块拆成半页。

Front matter must contain exactly those six fields, with no parallel `title`, `source_manifest`, or other identity fields. The body must be nonempty and complete. The 65,536-byte ceiling applies only to UTF-8 body bytes after the closing delimiter, excluding front matter. Version 1 has no pagination, so never split a safety warning or code block across pages.

## 内容边界 / Content boundary

- 用稳定 ID 引用板卡、元器件和配方，不重新声明针脚、电压、编译或实物验证状态。
- 不包含脚本、安装钩子、依赖、可执行文件或 canonical YAML。
- 来源核对、代码编译、固件烧录、串口/网络和实物效果是不同证据门，不能互相代替。
- 本地 override 可以提供实验内容，但必须保持 `provenance=local_override`，不能冒充官方包。

- Refer to boards, components, and recipes by stable ID; do not restate canonical pins, voltages, or verification gates.
- Do not include scripts, hooks, dependencies, executables, or canonical YAML.
- Source review, compilation, upload, serial/network operation, and physical effects remain separate evidence gates.
- Local overrides may hold experiments, but must remain visibly labelled `provenance=local_override`.

## 发布前检查 / Before publication

先按 [知识来源管线](knowledge-source-pipeline.md) 完成清洗、来源核对、复核和发布批准，再按 [知识包格式](pack-format.md) 构建只读 `.cmpack`。只有 `publication_approved` 的页面可以进入官方知识包；核心 ZIP 只带紧凑索引，不带这些正文。

Complete cleaning, source review, human review, and publication approval before building the read-only `.cmpack`. Only `publication_approved` pages may enter an official knowledge pack. The Core ZIP carries compact indexes, never these detailed bodies.
