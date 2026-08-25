# ChatCAD MakerLab 中文名牌设计

## 问题

WorkBuddy 曾为“孙大卫”名牌直接生成 `text(..., font="Microsoft YaHei")`。这是 Windows 本机字体名，不在 MakerLab 当前字体面板中，因此三个汉字显示为缺字方框。改成 `SimHei` 或 `SimSun` 仍是同一类错误。

## 方案

新增 `design_kind=nameplate`。ChatCAD 返回轻量 `makerlab-code`，默认使用 MakerLab 当前实测支持的 `Noto Sans SC:style=Regular`。文字内容、长度、宽度、厚度、圆角、钥匙孔、文字大小、位置和凸起高度都可在 MakerLab 调整。交付代码时必须提醒用户先点击代码面板底部带 T 的放大镜图标（字体），勾选该精确字体；干净页面实测显示，只写字体名而未选择字体不会加载字形。

WorkBuddy 初始化指令同时增加硬约束：MakerLab 中文不得建议 `Microsoft YaHei`、`SimHei`、`SimSun`。当前字体面板共 8,267 个条目，其中元数据标记的中文相关字体有 17 个家族、72 个家族/样式条目；这是 2026-08-25 的动态快照，不是永久兼容承诺。若所需字形仍缺失，再使用 ChatMaker 内置 CJK 字体转 `polygon()` 的备用方案。

## 验收

- “孙大卫”名牌无需板卡即可生成。
- 返回代码包含可编辑 `cn_text`、原生 `text()` 和精确字体名 `Noto Sans SC:style=Regular`。
- MakerLab 代码路线不创建 STL、预览或输出目录。
- 代表性“孙大卫”代码在 MakerLab 真实页面选择字体后正确显示；实体打印与孔位适配仍为未验证。
