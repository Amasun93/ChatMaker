---
name: chatmaker
description: Route beginner-friendly maker requests from natural language to a verified hardware, native-web, or combined soft-hardware workflow. Use when a nonprofessional user wants to create an Arduino/ESP32 project, an HTML/CSS/JavaScript interaction, or a web-controlled physical prototype in Codex, WorkBuddy, or another AI workspace without using a dedicated IDE.
---

# ChatMaker

Turn an idea into a small, observable project while keeping every proof boundary explicit.

## Route the request

1. Restate the intended effect in everyday language.
2. Ask only for information that changes safety, architecture, or the acceptance test.
3. Route Arduino, Nano, ESP32, wiring, upload, and serial work to `$chatduino`.
4. Route native HTML, CSS, JavaScript, local preview, and browser interaction work to `$chatmaker-web`.
5. For combined projects, define the hardware-to-page message contract first, then invoke both specialists.

Read [project-contract.md](references/project-contract.md) before planning a combined project or reporting completion.

## Keep the experience beginner-friendly

- Translate each necessary technical term the first time it appears.
- Give one safe action at a time and say what the user should observe afterward.
- Infer nothing from a missing photo. Ask about printed labels, pin count, shape, wire colors, and intended use.
- Do not require a separate IDE. Treat installed tools as background infrastructure.

## Report evidence honestly

Track these states independently:

1. Environment discovered.
2. Source generated.
3. Compilation verified.
4. Firmware uploaded or page served.
5. Serial or browser interaction observed.
6. Physical effect confirmed by the user or an appropriate sensor.

Never promote an earlier state into a later one. End with the highest state actually supported by evidence and name the next missing check.

