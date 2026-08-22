# ChatCAD basic mechanical recipes

Read this reference only for basic spur gears, racks, shafts, bushings or the simple brackets generated with them.

## Supported projects

- `design_kind=gear_pair`: one driver gear, one driven gear, two shafts, two bushings and a two-axis plate bracket.
- `design_kind=rack_and_pinion`: one pinion, one rack, one shaft, one bushing and a simple plate bracket.

Both stay under `mode=chat3d`. Each project exports an assembled SCAD/STL, individual component SCAD/STL files, `project.json`, and an adjustable browser laboratory.

These standalone mechanisms do not require `board_id`. Require an exact board or component profile only when the bracket or mechanism must fit that hardware.

## Ask only for decisions that matter

Prefer the visible outcome first. A beginner can give a desired ratio and approximate size; convert that into a small set of parameters. Ask for a real shaft diameter when the model must fit an existing motor or axle. Do not invent it from a board or motor name.

| Parameter | Default | Accepted range |
|---|---:|---:|
| `gear_module` | 2.0 mm | 0.5–5.0 mm |
| `pressure_angle` | 20° | 14.5–30° |
| `gear_thickness` | 6.0 mm | 2–20 mm |
| `shaft_diameter` | 5.0 mm | 2–20 mm |
| `shaft_clearance` | 0.20 mm per side | 0.05–1.0 mm |
| `backlash` | 0.15 mm | 0–0.8 mm |
| `driver_teeth` / `pinion_teeth` | 12 / 16 | 8–80 |
| `driven_teeth` | 24 | 8–120 |
| `rack_teeth` | 12 | 4–80 |

The generator derives pitch diameter as `module × teeth`, standard gear-pair center distance as half the sum of pitch diameters, ratio as `driven_teeth / driver_teeth`, and rack circular pitch as `π × module`. Gear and rack must share module and pressure angle.

## Keep the feedback loop small

The deterministic recipe records derived values and checks in `project.json`. If an invalid combination such as an oversized shaft removes the gear root, explain which measurement must change. Automatically recompute safe derived values such as center distance; do not repeatedly rewrite the design or guess a physical measurement.

## Evidence limits

- A passed relationship check means the formulas and bounded parameters are internally consistent.
- The assembled preview shows static placement only; it is not collision, motion, strength or lifetime simulation.
- `model_generated=verified` does not prove the files opened in a slicer.
- `physical_fit=unverified` remains until real gears, shafts and clearances are printed and tested.

For a first print, recommend a small gear pair or shaft-hole coupon before the complete bracket.

Helical, bevel, worm, planetary and internal gears, belt drives, cams, complex linkages and engineering load analysis are outside this first recipe set.
