# ChatMaker 知识库 章节格式 / ChatMaker Knowledge page format

ChatMaker 知识库 (ChatMaker Knowledge) is a passive page layer for people and AI.
It may explain a board, safety, toolchains, examples, and protocols, but must
not duplicate or replace canonical facts in `packs/boards`, `packs/components`, or
`packs/recipes`.

## 一页一个章节 / One section per page

The filename must match the `section_id` in the compact index:

```text
knowledge/sections/<section-id>.md
```

Each page uses UTF-8, LF line endings, and begins with this YAML front matter:

```yaml
---
schema_version: "1.0"
kind: knowledge-page
stable_id: arduino-nano-classic-start-here
board_id: arduino-nano-classic
section_id: start-here
source_refs:
  - source-arduino-nano-classic-documentation
---
```

Front matter must contain exactly these six fields, with no parallel `title`,
`source_manifest`, or other identity fields. The body must be nonempty and
complete. The 65,536-byte ceiling counts only UTF-8 body bytes after the closing
delimiter; it excludes front matter. Version 1 has no pagination, so never split
a safety warning or code block across pages.

## 内容边界 / Content boundary

- Refer to boards, components, and recipes by stable ID; do not restate
  canonical pins, voltages, compilation, or physical-verification status.
- Do not include scripts, installation hooks, dependencies, executables, or
  canonical YAML.
- Source review, code compilation, firmware upload, serial or network runtime,
  and physical effects are separate evidence gates.
- A local override may provide experiments, but must remain visibly labelled
  `provenance=local_override` and cannot claim to be an official pack.

## 发布前检查 / Before publication

Complete cleaning, source review, human review, and publication approval before
building a read-only `.cmpack`. Only `publication_approved` pages may enter an
official knowledge pack. The Core ZIP carries compact indexes, never detailed
bodies.
