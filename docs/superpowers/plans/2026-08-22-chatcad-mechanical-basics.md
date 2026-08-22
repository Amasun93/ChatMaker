# ChatCAD Mechanical Basics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic, beginner-adjustable spur gear pair and rack-and-pinion projects to the existing ChatCAD `chat3d` entry.

**Architecture:** Keep enclosure generation unchanged. Route non-enclosure `parameters.design_kind` values from `chat3d.generate()` into a focused `mechanics.py` recipe module that derives geometry, runs relationship checks, writes component/assembly artifacts, and builds one browser lab. No new runtime dependency or executable generated code is introduced.

**Tech Stack:** Python 3.11+, OpenSCAD text output, pure-Python ASCII STL triangulation, dependency-free HTML Canvas.

**Spec:** `docs/plans/2026-08-22-chatcad-mechanical-basics-design.md`

## Global Constraints

- Keep one `cad_generate` tool and one `mode=chat3d` route.
- Default `design_kind=enclosure` must preserve existing output and tests.
- Support only `gear_pair` and `rack_and_pinion` in this milestone.
- Do not add LangGraph, Aider, build123d, external APIs, or package dependencies.
- Keep `model_generated`, `file_opened`, and `physical_fit` separate.
- Use focused tests plus one representative browser path.

---

### Task 1: Deterministic mechanical geometry and project contract

**Files:**
- Create: `runtime/chatmaker/cad/mechanics.py`
- Create: `tests/test_chat3d_mechanics.py`
- Modify: `runtime/chatmaker/cad/chat3d.py`

**Interfaces:**
- Consumes: `mechanics.generate(request, profile, output, name)` with `parameters.design_kind` equal to `gear_pair` or `rack_and_pinion`.
- Produces: the existing `cad_generate` result shape plus component files; `project.json` contains `design_brief`, `parameters`, `components`, `checks`, and evidence states.

- [x] **Step 1: Write the failing geometry and output tests**

```python
def test_gear_pair_derives_ratio_and_center_distance(self):
    result = generator.generate_project({
        "mode": "chat3d", "board_id": "arduino-uno-r3",
        "project_name": "gear-pair", "output_dir": folder,
        "parameters": {"design_kind": "gear_pair", "gear_module": 2,
                       "driver_teeth": 12, "driven_teeth": 24},
    })
    project = json.loads(Path(result["files"]["project"]).read_text("utf-8"))
    self.assertEqual(project["design_brief"]["derived"]["ratio"], 2.0)
    self.assertEqual(project["design_brief"]["derived"]["center_distance"], 36.0)
```

- [x] **Step 2: Run the focused test and verify RED**

Run: `$env:PYTHONPATH="$PWD/runtime"; python -m unittest tests.test_chat3d_mechanics -v`

Expected: FAIL because `design_kind=gear_pair` is not implemented.

- [x] **Step 3: Implement bounded parameter parsing, involute outlines, rack geometry, extrusion, checks, and artifact writing**

Implement these stable boundaries in `mechanics.py`:

```python
def derive(values: dict[str, Any]) -> dict[str, Any]: ...
def gear_outline(teeth: int, module: float, pressure_angle: float,
                 backlash: float, bore_diameter: float) -> list[tuple[float, float]]: ...
def generate(request: dict[str, Any], profile: dict[str, Any],
             output: Path, name: str) -> dict[str, Any]: ...
```

Route from `chat3d.generate()` only when `design_kind != "enclosure"`.

- [x] **Step 4: Run the focused test and verify GREEN**

Run: `$env:PYTHONPATH="$PWD/runtime"; python -m unittest tests.test_chat3d_mechanics -v`

Expected: gear-pair, rack-and-pinion, invalid-shaft, and enclosure-regression tests pass.

### Task 2: Adjustable browser laboratory and MCP surface

**Files:**
- Modify: `runtime/chatmaker/cad/mechanics.py`
- Modify: `runtime/chatmaker/integrations/workbuddy_mcp.py`
- Modify: `tests/test_chat3d_mechanics.py`
- Modify: `tests/test_cad.py`

**Interfaces:**
- Consumes: derived mechanism parameters embedded as JSON.
- Produces: `preview-lab.html` with sliders, static component placement, status/check cards, and SCAD/STL downloads generated from current page state.

- [x] **Step 1: Add failing assertions for the new MCP parameters and browser behavior markers**

Assert the real generated page exposes `design_kind`, recalculates `center_distance`, draws both supported mechanism types, and contains component/assembly export controls.

- [x] **Step 2: Run the focused tests and verify RED**

Run: `$env:PYTHONPATH="$PWD/runtime"; python -m unittest tests.test_chat3d_mechanics tests.test_cad -v`

- [x] **Step 3: Implement the browser lab and extend only the existing `cad_generate.parameters` schema**

Keep `additionalProperties: false`; add explicit numeric bounds matching Python validation.

- [x] **Step 4: Run the focused tests and verify GREEN**

Run: `$env:PYTHONPATH="$PWD/runtime"; python -m unittest tests.test_chat3d_mechanics tests.test_cad -v`

### Task 3: Skill routing, browser verification, and regression

**Files:**
- Modify: `skills/chatcad/SKILL.md`
- Create: `skills/chatcad/references/mechanical-basics.md`
- Modify: `tests/test_skill_validation.py` only if observable validation requires it.

**Interfaces:**
- Consumes: user requests for spur gears, racks, shafts, bushings, or basic brackets.
- Produces: concise routing to `mode=chat3d` with the appropriate `design_kind`, while preserving measurement and physical-fit boundaries.

- [x] **Step 1: Update the Skill entrypoint concisely and put formulas/limits in the conditional reference**

Do not duplicate the full reference in `SKILL.md`.

- [x] **Step 2: Run skill validation and focused Python regression**

Run: `python scripts/validate_skills.py`

Run: `$env:PYTHONPATH="$PWD/runtime"; python -m unittest tests.test_chat3d_mechanics tests.test_chat3d tests.test_cad tests.test_cad_text -v`

- [x] **Step 3: Serve one generated lab and verify the representative browser flow**

Generate a 12:24 gear pair, serve its output on `127.0.0.1`, change a tooth count, confirm center distance and preview update, trigger SCAD/STL downloads, and confirm no browser console errors.

- [x] **Step 4: Review the final diff and commit the isolated branch**

Stage only the plan, mechanics runtime, focused tests, MCP schema, and ChatCAD Skill files.
