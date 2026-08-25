<p align="right">
  <b>English</b> · <a href="README.md">简体中文</a>
</p>

# ChatMaker

**An AI creative partner for beginners building delightful hardware and web projects.**

ChatMaker helps teachers, students, and hackathon participants move from a clear request or a rough idea to an implemented and verified project. The user chooses the direction and judges the visible result. ChatMaker handles concept development, professional implementation, tools, and evidence.

ChatMaker is the only user entry. ChatDuino, ChatWeb, and ChatCAD remain separately maintained internal specialists invoked by ChatMaker.

Install the current Alpha through the host's native SkillHub or GitHub Skill flow, then: "Use $chatmaker as the only user entry." Ordinary installation does not run `chatmaker-install auto`, scan Codex/WorkBuddy, or register MCP. Source developers who need local CLIs may run `python -m pip install -e .` followed by `chatmaker-install local`.

> Early development status: [`v0.1.0-rc5`](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc5) is the latest packaged prerelease. Current source restores Mind+ 2.x as the preferred Starcore backend and keeps local CLI execution independent from optional WorkBuddy MCP registration. Physical evidence remains board-specific rather than inferred from software checks.

Current post-rc5 source is preparing a minimal `ChatMaker-Core-<version>.zip` plus four board-specific ChatMaker Knowledge packs. This work does not create a new GitHub Release; rc5 remains the current public prerelease.

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

The current source Core contains the Python runtime, four Skill directories, 5 boards, 20 components, 23 recipes, four compact Knowledge indexes, schemas, and current runnable examples. UNIHIKER M10 is an alpha source-level route with a canonical board record, Skill guidance, project checker, and example; it does not yet have a signed Knowledge pack or physical-board evidence. The Core deliberately excludes detailed Knowledge bodies, the knowledge workspace, tests, optional `.cmpack` artifacts, and development caches.

When an AI first requests a detailed board section, `chatmaker-knowledge` defaults to automatic installation. It accepts a pack only after checking the official registry signature, immutable URL, length, SHA-256, manifest, and every payload file. Later reads reuse the verified installation. An installed version remains readable after offline revalidation; an exact cache can authorize a new offline install only while its signed receipt is unexpired.

Automatic installation is limited to passive knowledge pages. It never installs drivers, Mind+, Arduino cores, Node, Chromium, PATH changes, hooks, or administrator-level software. The base Skill works without MCP. `chatmaker-install local` checks local capabilities without host scanning; the old multi-host `auto` path is retained only as an optional developer tool.

```powershell
chatmaker-knowledge --request-json '{"action":"section","board_id":"arduino-nano-classic","consumer":"chatduino","section_id":"identify-and-safety"}'
chatmaker-pack status chatmaker-board-arduino-nano-classic-knowledge
chatmaker-pack update chatmaker-board-arduino-nano-classic-knowledge
chatmaker-pack rollback chatmaker-board-arduino-nano-classic-knowledge --version 1.0.0
```

Experiments belong in a separate local override directory and stay labelled `provenance=local_override`; they cannot impersonate official content. See the [installation guide](docs/installation.md) for cache, offline, update, and rollback instructions.

## rc5 public prerelease

The current public prerelease is [`v0.1.0-rc5`](https://github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc5). rc1, rc2, rc3, and rc4 remain historical releases with their original artifacts and verification records.

Users can download the rc5 ZIP and matching `.sha256` from GitHub Releases, verify the archive, and then install it. Public `main` contains the current source. Neither route turns software tests or compilation into evidence of real upload, serial, network, or physical behavior.

rc5 contains fourteen recipes and a WorkBuddy stdio server `1.7.0` with 23 tools: 2 catalog tools, 5 Nano tools, 5 Uno tools, 5 ESP32 tools, and 6 serial tools. `chatmaker-route` performs executable hardware/web/combined routing. `chatmaker-web-plan` asks at most two load-bearing questions or returns two or three curated directions; expanded directions and `chatmaker-web-playground` require explicit `--advanced`. Real Chromium automation covers the classroom, simulated-hardware, ESP32 AP, and advanced-playground pages.

Nano and Uno continue to use Mind+ 1.x/2.x. ESP32 uses only an official Arduino CLI, the locked official core `esp32:esp32@3.3.11`, and exact FQBN `esp32:esp32:esp32doit-devkit-v1`. The AP page keeps `examples/chatweb/esp32-ap-control.html` as its only editable source and generates the embedded firmware header with `chatmaker-web-embed`. Compilation, upload, browser/serial/network operation, power-cycle, and physical effects remain separate gates. See the bilingual [installation guide](docs/installation.md) and [rc5 release notes](https://github.com/Amasun93/ChatMaker/blob/main/RELEASE_NOTES.md).

```powershell
Get-FileHash .\ChatMaker-0.1.0-rc5.zip -Algorithm SHA256
Get-Content .\ChatMaker-0.1.0-rc5.zip.sha256
Expand-Archive .\ChatMaker-0.1.0-rc5.zip -DestinationPath .
Set-Location .\ChatMaker-0.1.0-rc5
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

Read the [creative partner design](https://github.com/Amasun93/ChatMaker/blob/main/docs/plans/2026-08-14-chatmaker-creative-partner-design.md) and [implementation plan](https://github.com/Amasun93/ChatMaker/blob/main/docs/plans/2026-08-14-chatmaker-v0.1-implementation.md) for current scope and evidence.

Current source uses WorkBuddy stdio server `1.18.0` with 38 tools, including local OpenSCAD status/preparation and ChatCAD generation. The public rc5 paragraph above remains historical and still describes the rc5 artifact accurately.

## License

Apache-2.0
