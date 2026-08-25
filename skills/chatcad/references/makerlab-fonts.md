# MakerLab font evidence and safe text policy

Checked 2026-08-25.

## Live editor evidence

- [MakerLab China](https://makerworld.com.cn/zh/makerlab) lists the **参数化模型编辑器** as the official OpenSCAD customization surface.
- [Bambu Lab Wiki: MakerWorld release notes](https://wiki.bambulab.com/en/makerworld/release-note/makerworld-release-notes) states that OpenSCAD scripts are validated, previewed and customizable on MakerWorld model pages.
- The live editor at <https://makerworld.com.cn/zh/makerlab/parametricModelMaker?pageType=generator> displayed **筛选 8267** in its **字体** panel and loaded these MakerLab content resources:
  - [fonts-show-0.0.1.json](https://makerworld.bblmw.cn/makerworld/makerlab/content-generator/openscad/fonts-show-0.0.1.json): 8,267 exact selectable family/style strings.
  - [fonts-0.9.0.json](https://makerworld.bblmw.com/makerworld/makerlab/content-generator/openscad/fonts-0.9.0.json): 1,790 family metadata records, including language subsets.
- The official landing page, FAQ and release notes do not version-lock this list. Treat the counts and entries below as a 2026-08-25 runtime snapshot; the live **字体** panel remains the current source of truth.

## Current Chinese-capable families

The metadata snapshot marks 17 families as `chinese-simplified`, `chinese-traditional`, or `chinese-hongkong`, producing 72 selectable family/style entries.

- Simplified Chinese: `Liu Jian Mao Cao`, `Long Cang`, `Ma Shan Zheng`, `Noto Sans SC`, `Noto Serif SC`, `ZCOOL KuaiLe`, `ZCOOL QingKe HuangYou`, `ZCOOL XiaoWei`, `Zhi Mang Xing`.
- Traditional Chinese: `Noto Sans TC`, `Noto Serif TC`.
- Hong Kong / Traditional: `Cactus Classical Serif`, `Chocolate Classical Sans`, `LXGW WenKai Mono TC`, `LXGW WenKai TC`, `Noto Sans HK`, `Noto Serif HK`.

Exact style forms:

- `Noto Sans SC`, `Noto Sans TC`, and `Noto Sans HK`: base family plus `Black`, `Bold`, `ExtraBold`, `ExtraLight`, `Light`, `Medium`, `Regular`, `SemiBold`, and `Thin` as `Family:style=Weight`.
- `Noto Serif SC`, `Noto Serif TC`, and `Noto Serif HK`: base family plus `Black`, `Bold`, `ExtraBold`, `ExtraLight`, `Light`, `Medium`, `Regular`, and `SemiBold`.
- `LXGW WenKai Mono TC` and `LXGW WenKai TC`: `Bold`, `Light`, and `Regular`.
- Every remaining Chinese-capable family above exposes `:style=Regular`.

Prefer the explicit default `Noto Sans SC:style=Regular` for ordinary Simplified Chinese nameplates. It successfully rendered “孙大卫” in MakerLab on 2026-08-25.

## Operating rule

1. Default Simplified Chinese nameplates to `Noto Sans SC:style=Regular` and native OpenSCAD `text()` so the wording remains editable.
2. Give the required setup step with every such code block: in the code panel, click the bottom magnifying-glass icon with a **T** (字体), search and tick the exact font, confirm, then generate. A clean-page test showed that code alone did not load the font; after selection, “孙大卫” rendered correctly.
3. Do not infer MakerLab support from fonts installed on Windows. In particular, `Microsoft YaHei`, `SimHei`, and `SimSun` must not be offered as a fallback.
4. If a required character still renders as tofu or a selected family disappears from the live list, bake the wording to `polygon()` contours with ChatMaker's bundled CJK font. Keep size, position and extrusion depth parameterized, and explain that changing characters then requires regeneration in ChatCAD.
