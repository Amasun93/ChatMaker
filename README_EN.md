<p align="right">
  <b>English</b> · <a href="README.md">简体中文</a>
</p>

# ChatMaker

**An AI creative partner for beginners building delightful hardware and web projects.**

ChatMaker helps teachers, students, and hackathon participants move from a clear request or a rough idea to an implemented and verified project. The user chooses the direction and judges the visible result. ChatMaker handles concept development, professional implementation, tools, and evidence.

ChatMaker is the only user entry. ChatDuino, ChatWeb, and ChatCAD remain separately maintained internal specialists invoked by ChatMaker.

Install the current Beta from GitHub `main` through the host's native GitHub Skill flow, then: "Use $chatmaker as the only user entry." Ordinary installation does not scan Codex/WorkBuddy or install a separate tool service. Source developers who need local CLIs may run `python -m pip install -e .` followed by `chatmaker-install local`.

> Current version: **0.2.0-beta.1**. The maintainer reports more than 20 invited testers, and GitHub `main` is the recommended source. Physical evidence remains board-specific rather than inferred from software checks.

See the beginner-facing [WHAT'S NEW](WHATS_NEW.md) for a short summary of this update.

Current source includes a Windows x64 ChatMaker-managed Starcore CLI path. It prepares a locked Arduino CLI, Mind+ public ESP32 core, and exact mPython/OLED/font libraries without requiring the Mind+ desktop application. Existing Mind+ 1.8.x and 2.x installations remain compatible fallbacks.

## Architecture

```text
ChatMaker
├─ ChatDuino   hardware, wiring, firmware, compile, upload, serial
├─ ChatWeb     front-end creation, classroom tools, device UI, browser checks
└─ ChatCAD     parameterized 2D/3D fabrication design and preview
```

- **ChatMaker** adapts to how clear the user's idea is and routes the project.
- **ChatDuino** turns effects into safe wiring, complete firmware, compilation, upload, and physical checks.
- **ChatWeb** proposes two or three curated visual directions and builds classroom tools, creative interactions, and hardware interfaces.
- **ChatCAD** creates adjustable laser-cut drawings and 3D-printable models from trusted mechanical facts.

Beginner projects use one self-contained HTML file by default. Advanced style catalogs and a playground appear only when requested. Wiring uses one plain `text` block by default; SVG diagrams are optional and never replace the text source of truth.

## Philosophy

> ChatMaker = creative-partner philosophy + professional facts + executable tools + verification evidence

Skills guide judgment and define facts that must not be guessed. Scripts and runtime tools handle repeatable or fragile operations. Knowledge packs hold boards, components, libraries, examples, and visual patterns for progressive loading.

Compilation, firmware upload, browser interaction, serial evidence, and physical effects remain separate completion gates.

## Progressive board knowledge

The current source Core contains the Python runtime, four Skill directories, 7 boards, 21 components, 26 recipes, six compact Knowledge indexes, schemas, and current runnable examples. UNIHIKER M10 is an alpha source-level route with a canonical board record, Skill guidance, project checker, and example; it does not yet have a signed Knowledge pack or physical-board evidence. The Core deliberately excludes detailed Knowledge bodies, the knowledge workspace, tests, optional `.cmpack` artifacts, and development caches.

When an AI first requests a detailed board section, `chatmaker-knowledge` defaults to automatic installation. It accepts a pack only after checking the official registry signature, immutable URL, length, SHA-256, manifest, and every payload file. Later reads reuse the verified installation. An installed version remains readable after offline revalidation; an exact cache can authorize a new offline install only while its signed receipt is unexpired.

Automatic installation is limited to passive knowledge pages. It never installs drivers, Mind+, Arduino cores, Node, Chromium, PATH changes, hooks, or administrator-level software. `chatmaker-install local` checks local capabilities without discovering or modifying an AI host.

```powershell
chatmaker-knowledge --request-json '{"action":"section","board_id":"arduino-nano-classic","consumer":"chatduino","section_id":"identify-and-safety"}'
chatmaker-pack status chatmaker-board-arduino-nano-classic-knowledge
chatmaker-pack update chatmaker-board-arduino-nano-classic-knowledge
chatmaker-pack rollback chatmaker-board-arduino-nano-classic-knowledge --version 1.0.0
```

Experiments belong in a separate local override directory and stay labelled `provenance=local_override`; they cannot impersonate official content. See the [installation guide](docs/installation.md) for cache, offline, update, and rollback instructions.

See the [Beta roadmap](docs/roadmap.md), [creative partner design](https://github.com/Amasun93/ChatMaker/blob/main/docs/plans/2026-08-14-chatmaker-creative-partner-design.md), and [implementation plan](https://github.com/Amasun93/ChatMaker/blob/main/docs/plans/2026-08-14-chatmaker-v0.1-implementation.md) for current scope and evidence.

Current source removes the historical 38-tool stdio adapter and multi-host scanner. The same local capabilities are exposed through the smaller `chatmaker-*` CLI set. Historical rc5 build evidence remains archived in `RELEASE_NOTES.md`, but its GitHub Release and tag have been withdrawn.

## License

Apache-2.0
