# ChatWeb Single-File Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build ChatWeb's first deterministic runtime so a beginner request can receive three curated directions, produce one polished self-contained HTML file, and open a localhost-only preview with browser-verifiable interactions.

**Architecture:** Keep creative judgment in the ChatWeb Skill and store reusable visual directions in a small versioned catalog. A focused Python generator converts one accepted direction plus beginner-friendly content into a self-contained HTML document. A separate preview module owns localhost serving so generation, serving, and browser evidence remain independent.

**Tech Stack:** Python 3.11+, dataclasses, JSON, `html.escape`, `http.server`, native HTML/CSS/JavaScript, `unittest`, Playwright browser verification.

## Global Constraints

- Generate exactly one HTML file by default with embedded CSS and JavaScript.
- Offer three curated directions for a vague request; do not expose the advanced playground by default.
- Support a classroom tool and a simulated hardware interface without React, Vue, a database, login, cloud deployment, or external CDN assets.
- Bind preview to `127.0.0.1` by default. Require an explicit network flag before binding to another interface.
- Keep page rendering, browser interaction, hardware connectivity, and physical effects as separate evidence gates.
- Use at least 44 px touch targets, visible focus styles, reduced-motion support, and explicit ready, active, disconnected, and error states.
- Escape user-controlled text before placing it into HTML or JavaScript.

---

### Task 1: Curated Direction Catalog

**Files:**
- Create: `runtime/chatmaker/web/__init__.py`
- Create: `runtime/chatmaker/web/directions.py`
- Create: `tests/web/__init__.py`
- Create: `tests/web/test_directions.py`

**Interfaces:**
- Produces: `DesignDirection(id: str, name: str, feeling: str, primary_interaction: str, best_for: str, tradeoff: str, palette: tuple[str, ...], typography: str, motion: str)`.
- Produces: `suggest_directions(kind: str, desired_feeling: str | None = None, limit: int = 3) -> list[DesignDirection]`.

- [ ] **Step 1: Write the failing behavior tests**

```python
def test_vague_classroom_request_returns_three_distinct_directions():
    result = suggest_directions("classroom-tool")
    self.assertEqual(len(result), 3)
    self.assertEqual(len({item.id for item in result}), 3)
    self.assertTrue(all(item.feeling and item.primary_interaction for item in result))

def test_hardware_request_prioritizes_visible_connection_feedback():
    result = suggest_directions("hardware-interface")
    self.assertIn("连接", result[0].primary_interaction)
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `python tests/web/test_directions.py -v`

Expected: import failure because `chatmaker.web.directions` does not exist.

- [ ] **Step 3: Implement the immutable catalog and selector**

Create three deliberately different directions for each kind: an editorial classroom board, a playful tactile tool, and a calm projection-first tool; for hardware, prioritize a clear device-state console. Reject unknown kinds and clamp `limit` to 1-3.

- [ ] **Step 4: Run targeted and full tests**

Run: `python tests/web/test_directions.py -v`

Run: `python -m unittest discover -s tests -v`

Expected: all tests pass.

### Task 2: Self-Contained HTML Generator

**Files:**
- Create: `runtime/chatmaker/web/generator.py`
- Create: `tests/web/test_generator.py`
- Create: `examples/chatweb/classroom-pulse.html`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: `DesignDirection` from Task 1.
- Produces: `WebProjectRequest(kind: str, title: str, prompt: str, primary_label: str, direction_id: str)`.
- Produces: `GeneratedWebProject(path: Path, direction_id: str, evidence: dict[str, str])`.
- Produces: `generate_single_file(request: WebProjectRequest, output: Path) -> GeneratedWebProject`.
- Produces CLI: `chatmaker-web --request-json <json> --output <file>`.

- [ ] **Step 1: Write failing generator tests**

```python
def test_generator_writes_one_self_contained_html_file():
    project = generate_single_file(request, output)
    text = output.read_text(encoding="utf-8")
    self.assertEqual(project.path, output)
    self.assertIn("<style>", text)
    self.assertIn("<script>", text)
    self.assertNotIn("https://", text)
    self.assertIn('data-state="ready"', text)

def test_generator_escapes_user_text():
    request = replace(request, title='<script id="attack">bad()</script>')
    generate_single_file(request, output)
    text = output.read_text(encoding="utf-8")
    self.assertNotIn('<script id="attack">', text)
    self.assertIn("&lt;script", text)
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python tests/web/test_generator.py -v`

Expected: import failure because `chatmaker.web.generator` does not exist.

- [ ] **Step 3: Implement the minimal generator**

Render one complete document with CSS variables supplied by the selected direction. Include a strong display type stack without remote fonts, a textured background, one memorable asymmetric composition, a 44 px primary control, keyboard focus, reduced-motion handling, and a live status region. Classroom mode increments a visible response count. Hardware mode starts disconnected, lets the preview toggle a simulated connection, and labels it as simulation.

- [ ] **Step 4: Add CLI and checked-in example**

Add `chatmaker-web = "chatmaker.web.generator:main"` to `[project.scripts]`. Generate `examples/chatweb/classroom-pulse.html` through the CLI, never by manually maintaining a second template.

- [ ] **Step 5: Run generator tests, CLI smoke test, and full suite**

Run: `python tests/web/test_generator.py -v`

Run: `chatmaker-web --request-json '{"kind":"classroom-tool","title":"课堂脉冲","prompt":"今天哪一步最需要再讲一次？","primary_label":"我需要再讲一次","direction_id":"editorial-signal"}' --output examples/chatweb/classroom-pulse.html`

Run: `python -m unittest discover -s tests -v`

Expected: one HTML file is written and all tests pass.

### Task 3: Local Preview and Browser Evidence

**Files:**
- Create: `runtime/chatmaker/web/preview.py`
- Create: `tests/web/test_preview.py`
- Modify: `skills/chatweb/SKILL.md`
- Modify: `skills/chatweb/references/web-verification-contract.md`
- Modify: `README.md`
- Modify: `README_EN.md`

**Interfaces:**
- Produces: `PreviewAddress(host: str, port: int, url: str)`.
- Produces: `serve_preview(file: Path, host: str = "127.0.0.1", port: int = 0, allow_network: bool = False) -> tuple[ThreadingHTTPServer, PreviewAddress]`.
- Produces CLI: `chatmaker-web-preview <file> [--port N] [--allow-network]`.

- [ ] **Step 1: Write failing preview safety tests**

```python
def test_preview_defaults_to_loopback_and_serves_only_requested_file():
    server, address = serve_preview(html_file)
    self.addCleanup(server.shutdown)
    self.assertEqual(address.host, "127.0.0.1")
    self.assertEqual(urlopen(address.url).status, 200)

def test_non_loopback_host_requires_explicit_network_flag():
    with self.assertRaisesRegex(ValueError, "allow_network"):
        serve_preview(html_file, host="0.0.0.0")
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python tests/web/test_preview.py -v`

Expected: import failure because `chatmaker.web.preview` does not exist.

- [ ] **Step 3: Implement a focused preview server and CLI**

Serve only the chosen file and return 404 for unrelated paths. Start the server thread as a daemon, emit the exact local URL, and refuse non-loopback binding unless `allow_network=True`.

- [ ] **Step 4: Update the ChatWeb workflow and verification contract**

Require the runtime sequence: suggest directions, record the user's selected direction or explicit direct-build assumption, generate one file, start localhost preview, inspect console output, exercise the main control, and report rendering separately from any hardware claim.

- [ ] **Step 5: Run automated and browser verification**

Run: `python -m unittest discover -s tests -v`

Run: `python runtime/doctor.py --packs`

Run: `PYTHONUTF8=1 python C:/Users/asus/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/chatweb`

Open the generated localhost URL in Playwright. Verify the title renders, the primary button increases the visible count, the status live region changes, touch target height is at least 44 px, and the browser console has no errors. Save the exact observations under `docs/verification/` without claiming hardware connectivity.

- [ ] **Step 6: Final repository gate**

Run: `git diff --check`

Run: `python -m unittest discover -s tests -v`

Expected: clean diff check and zero test failures.
