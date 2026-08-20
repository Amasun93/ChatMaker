# ChatCAD 中文文字渲染交接文档（2026-08-20）

给接手优化的人（Codex 或其他 AI/开发者）。读完本文即可继续工作，不需要重新考古。

## 背景：要解决什么问题

ChatMaker 面向国内零基础开发者分发。用户用 ChatCAD 生成 3D 打印外壳并想在盒盖刻中文名字（姓名牌/铭牌）时，会撞上 OpenSCAD 的已知缺陷：

- OpenSCAD 2021.01（含 Bambu Studio 自定义参数实验室内嵌的 OpenSCAD）的 FreeType/fontconfig 栈渲染 CJK 字形出豆腐方块
- 已实测换字体无效（拓竹 HarmonyOS_Sans_SC、STHeiti Medium 均复现豆腐），是版本自身问题
- `starcore-student-maker` skill 的策略是回避（项目名默认英文/拼音，见其 `references/modeling.md:59`），不可复用于中文姓名牌场景

需求原文见 GitHub issue **Amasun93/ChatMaker#3**（中文环境适配清单，含后续待办）。

## 已实现方案（本轮完成）

**核心思路：彻底绕开 OpenSCAD 的字体渲染，字形在 Python 侧固化成几何。**

链路：fontTools 读系统字体 → 字形轮廓多边形 →
1. `.scad` 输出 `polygon()` + `linear_extrude()`（全程无 `text()`），任何 OpenSCAD 版本都能正确渲染
2. `.stl` 由纯 Python 三角化（ear clipping + 洞桥接），不调 OpenSCAD

### 改动文件清单

| 文件 | 内容 |
|---|---|
| `runtime/chatmaker/cad/text.py`（新增） | 字体查找、字形轮廓提取（自定义 Pen 展平 TrueType 二次/CFF 三次曲线）、轮廓分组、ear-clipping 三角化、SCAD polygon 生成 |
| `runtime/chatmaker/cad/chat3d.py` | `_engrave_plan()` 新参数 `engrave_text/text_size/text_depth/engrave_font`；`_scad()` 改为 customizer 格式 + `part` 模式 + `label_*` 参数；`_stl()` 追加文字三角形；`_lab()` 嵌入字形轮廓（网页导出 SCAD 同样带中文） |
| `runtime/chatmaker/integrations/workbuddy_mcp.py` | `cad_generate` 的 parameters 白名单加 4 个新参数 |
| `pyproject.toml` | dependencies 加 `fonttools>=4.47,<5` |
| `skills/chatcad/SKILL.md` | 第 8/9 条：中文文字用法与拓竹实验室工作流 |
| `tests/test_cad_text.py`（新增） | 10 项测试：几何单元 + 端到端 |

### 关键设计决策（踩过的坑，别再踩）

1. **轮廓方向**：TrueType 外轮廓是顺时针（y-up 下 signed area < 0），CFF 相反。不要按面积符号判断外/内轮廓，`_group_contours()` 用拓扑包含关系分组（偶数嵌套深度 = solid，奇数 = hole）。
2. **洞桥接方向**：合并洞进外轮廓时，洞必须以顺时针接入逆时针外轮廓（贡献负面积），否则 ear clipping 面积翻倍。
3. **SCAD 参数化**：文字 polygon 以文字自身中心为原点输出（`label_glyphs()` module），位置由 SCAD 侧 `label_on(cover_y)` + customizer 参数驱动——用户在拓竹实验室改盒子尺寸时文字仍居中。
4. **preview-lab.html 的 JS 导出**：字形轮廓已 JSON 嵌入页面，网页导出的 SCAD 与 CLI 导出同构。

### 已验证

- 本机 OpenSCAD 2021.01 命令行渲染：7800 facets，零 ERROR
- customizer 参数 `-D part=lid -D label_scale=2.0 -D label_depth=3` 全部生效（渲染 z 范围 0→5.0）
- 测试：`python -m unittest tests.test_cad_text tests.test_cad tests.test_chat3d`（31 项全绿）

## 已知边界与待优化项（按优先级）

1. **连笔字缺笔画**：部分字体的连笔设计（如微软雅黑"圈"：笔画与口框融合成单个 477 点自缠绕轮廓）在拓扑分组下会丢内部笔画。正确解法需要自交多边形拆分或 nonzero winding fill，成本较高。当前缓解：文档标注"姓名牌优先用常规结构字"。频率低（人名常用字绝大多数是规则嵌套轮廓）。
2. **字体三次解析**（已修）：`_engrave_plan` 已改为单次 `glyph_layout` + `scad_polygons_from_layout`/`triangles_from_layout` 复用。若再加文字功能，保持这个模式。
3. **随包开源中文字体**：当前依赖用户系统字体（Windows msyh/simhei、macOS PingFang、Linux Noto CJK）。计划打包思源黑体（SIL OFL 1.1 可再分发）subset 进 skill 资源，摆脱系统依赖。见 issue #3 第 3 项。
4. **OLED 中文字库引导**：chatduino/starcore 生成 OLED 中文显示代码时自动附带 U8g2/字库烧录方案。见 issue #3 第 2 项。注意掌控板目标不适用 U8g2（starcore troubleshooting 已有结论）。
5. **STL 文字与底板无布尔并集**：文字浮凸在盖面上方直接拼接三角形（空间不重叠所以合法）。若未来做"凹刻"（文字沉入表面），需要真正的 CSG 或改用 OpenSCAD 渲染。

## 环境注意

- 本机 Python 是 3.13.12，`tests/installers/test_bootstrap` 需要 Python 3.11（`python_3_11_required`），那些失败是预存环境问题，与本功能无关
- Git Bash 下 Windows Python 打不开 `/tmp/...` 路径，用相对路径或 `cygpath -w` 转换
- 验证 SCAD 用本机 OpenSCAD：`"/c/Program Files/OpenSCAD/openscad.exe" -o out.stl in.scad`（注意别用 `| grep` 提前关管道，会 SIGPIPE 杀掉渲染进程）

## 演示与验证材料

`~/Desktop/chatmaker-cjk-demo/`（用户桌面，不进仓库）：
- `starcore-nameplate.scad`（customizer 格式，可拖进拓竹自定义参数实验室）
- `starcore-nameplate.stl`（Python 直出）
- `openscad-rendered.stl`（OpenSCAD 2021.01 实渲染，中文不豆腐的实证）
- `文字验证.svg`（字形轮廓 vs 三角化投影对比图）

## 下一步建议

1. 用户在 Bambu Studio 实切一件验证实际打印效果
2. 确认后 commit（本轮改动仍在工作区未提交）
3. Codex 接手时从"待优化项"第 3 项（随包字体）开始，收益最大且独立

## 2026-08-20 接续进展：待优化项 3 已完成

- 已从 Adobe 官方 `source-han-sans` 仓库的固定提交生成字体子集。
- 子集覆盖可打印 ASCII 与 GB2312 定义的全部 7540 个字符/符号，适合常见简体中文姓名、班级和作品铭牌。
- 子集内部名称已改为 `ChatMaker CJK Sans`，遵守 SIL OFL 1.1 的 Reserved Font Name 条款。
- 默认查找顺序已改为：用户显式字体 → 随包字体 → 系统字体。
- 字体、OFL 许可证和可复现来源/哈希说明均位于 `runtime/chatmaker/cad/assets/`，并声明为 Python package data。
- 子集约 3.37 MiB；不追求覆盖生僻扩展汉字。需要范围外字符时，用户仍可通过 `engrave_font` 指定完整字体。

下一项仍是 OLED 中文字库引导；它属于 ChatDuino，不在本次 ChatCAD 字体打包范围内。

## 2026-08-20 接续进展：右侧预览中文轮廓已显示

- `preview-lab.html` 的右侧 Canvas 现在使用与 SCAD/STL 相同的字形轮廓绘制盖面中文，不调用 `fillText()`，因此不依赖浏览器中文字体。
- 本地浏览器实际打开“星核创客”示例，右侧模型已显示中文轮廓且没有豆腐方块。
- OpenSCAD 2021.01 对同一 SCAD 完整渲染成功：1195 facets、7 volumes、零错误。
- MakerWorld Parametric Model Maker 需要登录；当前 Chrome 未开启远程调试，因此在线导入仍保持待验收，不能写成已通过。
