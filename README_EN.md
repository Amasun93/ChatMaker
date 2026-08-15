<p align="right">
  <b>English</b> · <a href="README.md">简体中文</a>
</p>

# ChatMaker

**An AI creative partner for beginners building delightful hardware and web projects.**

ChatMaker helps teachers, students, and hackathon participants move from a clear request or a rough idea to an implemented and verified project. The user chooses the direction and judges the visible result. ChatMaker handles concept development, professional implementation, tools, and evidence.

> Early development status: `v0.1.0-rc5` is a local release candidate and has not been published on GitHub; rc4 remains the public release. rc5 includes Nano/Uno Mind+ compilation, controlled official ESP32 preparation and exact-FQBN compilation, the embedded AP page, executable routing and creative planning, an opt-in advanced playground, WorkBuddy 1.7.0 with 23 tools, and real Chromium automation. No matching physical-board evidence exists, so upload and physical behavior are not claimed.

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

## rc5 local candidate

The public release remains [`v0.1.0-rc4`](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc4). rc1, rc2, rc3, and rc4 remain historical releases with their original artifacts and verification records. rc5 is only a locally built candidate until commit, push, CI, tag, GitHub prerelease, and asset visibility have each been confirmed.

rc5 contains fourteen recipes and a WorkBuddy stdio server `1.7.0` with 23 tools: 2 catalog tools, 5 Nano tools, 5 Uno tools, 5 ESP32 tools, and 6 serial tools. `chatmaker-route` performs executable hardware/web/combined routing. `chatmaker-web-plan` asks at most two load-bearing questions or returns two or three curated directions; expanded directions and `chatmaker-web-playground` require explicit `--advanced`. Real Chromium automation covers the classroom, simulated-hardware, ESP32 AP, and advanced-playground pages.

Nano and Uno continue to use Mind+ 1.x/2.x. ESP32 uses only an official Arduino CLI, the locked official core `esp32:esp32@3.3.11`, and exact FQBN `esp32:esp32:esp32doit-devkit-v1`. The AP page keeps `examples/chatweb/esp32-ap-control.html` as its only editable source and generates the embedded firmware header with `chatmaker-web-embed`. Compilation, upload, browser/serial/network operation, power-cycle, and physical effects remain separate gates. See the bilingual [installation guide](docs/installation.md) and [rc5 release notes](RELEASE_NOTES.md).

```powershell
git clone https://github.com/Amasun93/ChatMaker.git
cd ChatMaker
python -m pip install -e .
python -m unittest discover -s tests -v
python runtime/doctor.py
chatmaker-catalog --request-json '{"action":"search","query":"relay","kind":"component"}'
chatmaker-route --request-json '{"hardware":{"board":"arduino-nano-classic"}}'
chatmaker-nano --request-json '{"action":"doctor"}'
chatmaker-uno --request-json '{"action":"doctor"}'
chatmaker-esp32 --request-json '{"action":"prepare-environment"}'
chatmaker-nano-examples --root examples/chatduino/nano
chatmaker-web-plan --brief-json '{"kind":"classroom-tool","idea":"collect class feedback","audience_scene":"students before class ends","desired_feeling":"clear and calm","primary_action":"choose the step to explain again"}'
chatmaker-web-embed examples/chatweb/esp32-ap-control.html examples/chatduino/esp32/ap-led-sensor/page_html.h --symbol CHATMAKER_AP_PAGE
chatmaker-web --request-json '{"kind":"classroom-tool","title":"Class pulse","prompt":"Which step needs another explanation?","primary_label":"Explain it again","direction_id":"editorial-signal"}' --output examples/chatweb/classroom-pulse.html
chatmaker-web-preview examples/chatweb/classroom-pulse.html
npm ci
npx playwright install chromium
npm run test:browser
```

Read the [creative partner design](docs/plans/2026-08-14-chatmaker-creative-partner-design.md) and [implementation plan](docs/plans/2026-08-14-chatmaker-v0.1-implementation.md) for current scope and evidence.

## License

Apache-2.0
