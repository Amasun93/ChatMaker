# Chat2D Parametric Box and Direct Manipulation Plan

> Scope: replace the current Chat2D draft inside the existing worktree. Keep one dependency-free generated HTML file; do not change Chat3D, installers, or publishing.

## Task 1: Lock the new contract

**Files:** `tests/test_chat2d.py`, `docs/plans/2026-08-21-chat2d-beginner-canvas-design.md`

- Test a dedicated model rather than HTML string presence alone.
- Require six orthogonal closed contours with no diagonal corner joins.
- Cover complementary male/female edge roles, three joint sizes, material thickness, fit compensation, internal/external dimensions, and optional lids.
- Require drag/drop hooks, automatic face detection, invalid-drop state, snap/restore behavior, visual templates, and synchronized label visibility.

## Task 2: Build the parametric geometry module

**Files:** `runtime/chatmaker/cad/box_model.py`, `runtime/chatmaker/cad/chat2d.py`

- Move panel layout and finger-joint outline generation into `box_model.py`.
- Generate each edge from symmetric margins and rectangular male/female segments that start and end on the base edge.
- Assign complementary edge roles to every mating pair.
- Make static SVG/DXF consume this model.

## Task 3: Replace form routing with direct manipulation

**Files:** `runtime/chatmaker/cad/chat2d.py`

- Remove the left rail, placed-item list, face buttons, selected-face dropdown, and hole editor.
- Add gallery drag ghosts and canvas hit testing.
- Determine the face from pointer position; show valid/invalid colors while dragging.
- On release clamp to the nearest valid point, or restore/cancel if the item cannot fit.
- Keep selection, rename, rotation, and delete as small secondary controls.

## Task 4: Add profile-backed visual templates

**Files:** `runtime/chatmaker/cad/chat2d.py`

- Build SVG thumbnails and placed graphics from reviewed outline, mounting-hole, and panel-feature records.
- Use center marks instead of guessed holes when diameter requires measurement.
- Preserve the same template geometry in SVG/DXF export.

## Task 5: Minimum sufficient verification

- Run focused Chat2D unit tests with the worktree runtime on `PYTHONPATH`.
- Generate one UNO project and use a real browser to drag a library item to a side panel, cross between panels, trigger invalid color/snap, toggle labels, and inspect SVG/DXF plus 3D preview.
- Confirm zero console errors and keep `physical_fit=unverified`.
