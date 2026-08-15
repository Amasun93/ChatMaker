<p align="right">
  <b>English</b> · <a href="README.md">简体中文</a>
</p>

# ChatMaker

**An AI creative partner for beginners building delightful hardware and web projects.**

ChatMaker helps teachers, students, and hackathon participants move from a clear request or a rough idea to an implemented and verified project. The user chooses the direction and judges the visible result. ChatMaker handles concept development, professional implementation, tools, and evidence.

> Early development status: the Nano/Mind+ runtime, a separate Uno/Mind+ adapter, and eleven compiled AVR examples are on public `main`. The development branch adds a strict DOIT ESP32 DevKit V1 compile-upload path plus an AP phone-control example. The exact official ESP32 core is not installed and no physical board is connected, so ESP32 compilation, upload, Wi-Fi, HTTP, and physical effects remain unverified.

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

The current public candidate is [`v0.1.0-rc4`](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc4). It includes the twelve-component learning pack, Chinese catalog search/get, ten compiled Nano examples, and an independent Uno adapter using `arduino:avr:uno` for Mind+ 1.x, `mindplus:avr:uno` for Mind+ 2.x, and a fixed 115200 upload rule. See the [installation guide](docs/installation.md). Physical upload and effects still require separate on-site evidence.

After rc4, the development branch contains fourteen recipes and a 23-tool WorkBuddy server: 2 catalog tools, 5 Nano tools, 5 Uno tools, 5 ESP32 tools, and 6 serial tools. The new `esp32_compile_upload` route requires the exact DOIT carrier profile and one non-Bluetooth wired port. The ESP32 AP example uses GPIO23 for a current-limited LED and GPIO34 for a 3.3 V 10 kOhm potentiometer, with a self-contained mobile control page. Its source contracts and simulated browser interaction are verified; exact-core compilation and every real-device gate are still open.

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
