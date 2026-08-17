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
6. For laser cutting call `cad_generate` with `mode=chat2d`. The white laboratory edits box dimensions, defaults to 3 mm wood, lets the user drag/label board or generic module footprints, keeps LaserMaker colors, previews the assembled box, and exports DXF/SVG.
7. For 3D printing call `cad_generate` with `mode=chat3d`. The white laboratory adjusts enclosure dimensions, wall, floor, lid and standoffs; its canvas supports mouse/touch rotation, wheel zoom and Shift-drag pan; export OpenSCAD/STL.
8. Give the user the returned `preview_lab` file. Explain that parameter changes in the page affect its next export. Keep the SCAD file as the editable source for Chat3D.

## Keep evidence clear

- Arduino Nano and Uno dimensions come from official Arduino CAD.
- The DOIT ESP32 DevKit V1 profile is a community reference because clone dimensions vary. Request a ruler or caliper measurement before a tight fit.
- Starcore v4.2.2 uses sanitized measurements derived from private DXF and STEP evidence. Do not expose or request manufacturing source files.
- A generated file is not a verified physical fit. Report `physical_fit=unverified` until the user tests the real board.

Read [verification.md](references/verification.md) when reporting dimensions, fit, or fabrication readiness.
