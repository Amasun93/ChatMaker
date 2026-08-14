<p align="right">
  <b>English</b> · <a href="README.md">简体中文</a>
</p>

# ChatMaker

**An AI creative partner for beginners building delightful hardware and web projects.**

ChatMaker helps teachers, students, and hackathon participants move from a clear request or a rough idea to an implemented and verified project. The user chooses the direction and judges the visible result. ChatMaker handles concept development, professional implementation, tools, and evidence.

> Early development status: the Nano/Mind+ runtime and ten compiled examples are on public `main`. The first structured pack contains twelve components and eleven recipes, exposed through catalog search/get tools with Chinese aliases. ChatWeb generates and previews self-contained classroom and simulated-hardware pages; physical upload and real hardware connectivity remain separate on-site gates.

## Architecture

```text
ChatMaker
├─ ChatDuino   hardware, wiring, firmware, compile, upload, serial
└─ ChatWeb     front-end creation, classroom tools, device UI, browser checks
```

- **ChatMaker** adapts to how clear the user's idea is and routes the project.
- **ChatDuino** turns effects into safe wiring, complete firmware, compilation, upload, and physical checks.
- **ChatWeb** proposes two or three curated visual directions and builds classroom tools, creative interactions, and hardware interfaces.

Beginner projects use one self-contained HTML file by default. Advanced style catalogs and a playground appear only when requested. Wiring uses one plain `text` block by default; SVG diagrams are optional and never replace the text source of truth.

## Philosophy

> ChatMaker = creative-partner philosophy + professional facts + executable tools + verification evidence

Skills guide judgment and define facts that must not be guessed. Scripts and runtime tools handle repeatable or fragile operations. Knowledge packs hold boards, components, libraries, examples, and visual patterns for progressive loading.

Compilation, firmware upload, browser interaction, serial evidence, and physical effects remain separate completion gates.

## Development preview

The current public candidate is [`v0.1.0-rc2`](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc2); it adds persistent serial list/open/read/expect/write/close tools to the published rc1 foundation. See the [installation guide](docs/installation.md). Physical upload and effects still require separate on-site evidence.

```powershell
git clone https://github.com/Amasun93/ChatMaker.git
cd ChatMaker
python -m pip install -e .
python -m unittest discover -s tests -v
python runtime/doctor.py
chatmaker-nano --request-json '{"action":"doctor"}'
chatmaker-nano-examples --root examples/chatduino/nano
chatmaker-web --request-json '{"kind":"classroom-tool","title":"Class pulse","prompt":"Which step needs another explanation?","primary_label":"Explain it again","direction_id":"editorial-signal"}' --output examples/chatweb/classroom-pulse.html
chatmaker-web-preview examples/chatweb/classroom-pulse.html
```

Read the [creative partner design](docs/plans/2026-08-14-chatmaker-creative-partner-design.md) and [implementation plan](docs/plans/2026-08-14-chatmaker-v0.1-implementation.md) for current scope and evidence.

## License

Apache-2.0
