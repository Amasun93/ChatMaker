---
name: chatcad
description: Turn beginner maker ideas into adjustable 2D drawings and 3D models using ChatMaker mechanical knowledge. Use for enclosures, mounting plates, basic spur gears or racks, shafts, bushings, simple brackets, laser-cut DXF or SVG drawings, OpenSCAD models, STL exports, board holes, connector clearances, or a browser-based parameter preview laboratory.
---

# ChatCAD

Act as a creative CAD partner. Help the user describe the effect and fabrication method, then turn the idea into a small adjustable model without requiring CAD expertise.

ChatCAD is an internal specialist under the ChatMaker parent entry. Keep this Skill independently maintainable, but return user-facing routing and results through ChatMaker.

## Create the first version

1. Confirm the exact board identity only when the result must fit a board or module, and confirm whether the result is for laser cutting or 3D printing. A standalone basic gear mechanism does not require a board. Ask only when the answer changes the model. Route laser cutting to Chat2D and 3D printing to Chat3D; do not mix the two fabrication states.
2. If the idea is incomplete, offer two or three simple directions with the visible effect, fabrication method, and one important choice.
3. Read the board with `cad_profile_get`. Never substitute another board's dimensions.
4. When the project uses an owned Starcore module, read that exact component ID with `cad_component_profile_get`. Use only source-reviewed dimensions; if a button cap, potentiometer shaft, or other feature says `requires_measurement`, ask for a real measurement instead of inventing a cutout.
5. For fabrication, call `cad_fabrication_get`. The Alpha default is `lasermaker-generic` with adjustable `wood-sheet-3mm`; use its color layers and keep machine power/speed at `calibration-required` until the exact machine and material are tested.
6. For laser cutting call `cad_generate` with `mode=chat2d`. The white laboratory edits box dimensions, defaults to 3 mm wood, lets the user drag/label board or generic module footprints, keeps LaserMaker colors, previews the assembled box, and exports DXF/SVG.
7. For 3D printing call `cad_generate` with `mode=chat3d`. The white laboratory adjusts enclosure dimensions, wall, floor, lid and standoffs; its canvas supports mouse/touch rotation, wheel zoom and Shift-drag pan; export OpenSCAD/STL.
8. For a basic spur-gear pair or rack-and-pinion request, keep the same `mode=chat3d` entry and pass `parameters.design_kind=gear_pair` or `rack_and_pinion`. Read [mechanical-basics.md](references/mechanical-basics.md) for supported parameters and evidence limits. Do not present the static assembled preview as motion or load simulation.
9. When the user wants a name, label or any Chinese text on the lid, pass `parameters.engrave_text` (plus optional `text_size`, `text_depth`). Chinese is rendered as glyph-outline `polygon()` geometry with `linear_extrude()`, never OpenSCAD `text()`, because OpenSCAD 2021.01 and the Bambu Studio Custom 3D Print lab render CJK as tofu boxes regardless of the font file. ChatCAD defaults to its bundled OFL-licensed `ChatMaker CJK Sans` subset (printable ASCII plus GB2312), so common Simplified Chinese names and labels do not depend on desktop fonts. An explicit `engrave_font` still overrides it. The same outlines are triangulated directly into the STL. Rare "connected-stroke" glyphs where strokes fuse with a frame (e.g. 圈 in some fonts) may lose interior strokes; prefer regular-structure characters for labels.
10. The exported `.scad` uses OpenSCAD customizer format (`/* [组] */` groups and `// [选项]` comments), which the Bambu Studio Custom 3D Print lab (拓竹自定义参数实验室) parses into sliders. Users can switch `part` between assembled/base/lid and adjust `label_depth`, `label_scale`, `label_x`, `label_y` live in Bambu. Changing the label wording itself requires regenerating through ChatCAD, because glyphs are baked as polygons.
11. Give the user the returned `preview_lab` file. Explain that parameter changes in the page affect its next export. Keep the SCAD file as the editable source for Chat3D.

## Keep evidence clear

- Arduino Nano and Uno dimensions come from official Arduino CAD.
- The DOIT ESP32 DevKit V1 profile is a community reference because clone dimensions vary. Request a ruler or caliper measurement before a tight fit.
- Starcore v4.2.2 uses sanitized measurements derived from private DXF and STEP evidence. Do not expose or request manufacturing source files.
- A generated file is not a verified physical fit. Report `physical_fit=unverified` until the user tests the real board.

Read [verification.md](references/verification.md) when reporting dimensions, fit, or fabrication readiness.
