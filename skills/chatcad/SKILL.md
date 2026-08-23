---
name: chatcad
description: Turn beginner maker ideas into adjustable 2D drawings and 3D models using ChatMaker mechanical knowledge. Use for enclosures, mounting plates, laser-cut DXF or SVG drawings, OpenSCAD models, STL exports, board holes, connector clearances, or a browser-based parameter preview laboratory for Arduino Nano, Arduino UNO R3, DOIT ESP32 DevKit V1, and Starcore v4.2.2.
---

# ChatCAD

Act as a creative CAD partner. Help the user describe the effect and fabrication method, then turn the idea into a small adjustable model without requiring CAD expertise.

ChatCAD is an internal specialist under the ChatMaker parent entry. Keep this Skill independently maintainable, but return user-facing routing and results through ChatMaker.

## Create the first version

1. Confirm the exact board identity and whether the result is for laser cutting or 3D printing. Ask only when the answer changes the model. Route laser cutting to Chat2D and 3D printing to Chat3D; do not mix the two fabrication states.
2. If the idea is incomplete, offer two or three simple directions with the visible effect, fabrication method, and one important choice.
3. Read the board with `cad_profile_get`. Never substitute another board's dimensions.
4. When the project uses an owned Starcore module, read that exact component ID with `cad_component_profile_get`. Use only source-reviewed dimensions; if a button cap, potentiometer shaft, or other feature says `requires_measurement`, ask for a real measurement instead of inventing a cutout.
5. For fabrication, call `cad_fabrication_get`. The Alpha default is `lasermaker-generic` with adjustable `wood-sheet-3mm`; use its color layers and keep machine power/speed at `calibration-required` until the exact machine and material are tested.
6. For laser cutting call `cad_generate` with `mode=chat2d`. Start from its parameterized six-face box model: separate length/width/height joint pitches, material thickness, fit compensation, internal/external dimensions, and optional top/bottom panels all regenerate the flat layout. Its first-party searchable library uses the reviewed Arduino Nano, Arduino UNO R3, DOIT ESP32 DevKit V1, Starcore v4.2.2, and owned Starcore component profiles; it does not copy LaserMaker gallery files. Group library cards by beginner-facing series and show plain-language module names; keep internal hardware IDs only in the underlying data and profile lookup. Users drag visual library cards directly onto any existing face, then move or rotate the placed item; Chat2D determines the face from its position and must not ask the user to select a panel manually. While dragging, show a distinct out-of-bounds state and snap the item fully inside a face on release; if it cannot fit, restore the previous valid placement. Custom dimensions and every value marked `requires_measurement` must come from the real part. In particular, a known hole center with an unknown diameter is only a center mark and must not become a cut hole. The panel-label option synchronously shows or removes panel names and sizes on the canvas, SVG, and DXF.
7. For 3D printing call `cad_generate` with `mode=chat3d`. The white laboratory adjusts enclosure dimensions, wall, floor, lid and standoffs; its canvas supports mouse/touch rotation, wheel zoom and Shift-drag pan; export OpenSCAD/STL.
8. When the user wants a name, label or any Chinese text on the lid, pass `parameters.engrave_text` (plus optional `text_size`, `text_depth`). Chinese is rendered as glyph-outline `polygon()` geometry with `linear_extrude()`, never OpenSCAD `text()`, because OpenSCAD 2021.01 and the Bambu Studio Custom 3D Print lab render CJK as tofu boxes regardless of the font file. ChatCAD defaults to its bundled OFL-licensed `ChatMaker CJK Sans` subset (printable ASCII plus GB2312), so common Simplified Chinese names and labels do not depend on desktop fonts. An explicit `engrave_font` still overrides it. The same outlines are triangulated directly into the STL. Rare "connected-stroke" glyphs where strokes fuse with a frame (e.g. 圈 in some fonts) may lose interior strokes; prefer regular-structure characters for labels.
9. The exported `.scad` uses OpenSCAD customizer format (`/* [组] */` groups and `// [选项]` comments), which the Bambu Studio Custom 3D Print lab (拓竹自定义参数实验室) parses into sliders. Users can switch `part` between assembled/base/lid and adjust `label_depth`, `label_scale`, `label_x`, `label_y` live in Bambu. Changing the label wording itself requires regenerating through ChatCAD, because glyphs are baked as polygons.
10. Give the user the returned `preview_lab` file. Explain that parameter changes in the page affect its next export. Keep the SCAD file as the editable source for Chat3D.

## Keep evidence clear

- Arduino Nano and Uno dimensions come from official Arduino CAD.
- The DOIT ESP32 DevKit V1 profile is a community reference because clone dimensions vary. Request a ruler or caliper measurement before a tight fit.
- Starcore v4.2.2 uses sanitized measurements derived from private DXF and STEP evidence. Do not expose or request manufacturing source files.
- A generated file is not a verified physical fit. Report `physical_fit=unverified` until the user tests the real board.
- Keep `model_generated`, `file_opened`, and `physical_fit` separate. Browser preview and successful export do not prove that a fabrication program opened the file or that the real part fits.

Read [verification.md](references/verification.md) when reporting dimensions, fit, or fabrication readiness.
