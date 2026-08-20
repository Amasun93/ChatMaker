---
name: chatweb
description: Act as a beginner front-end creative partner that creates and verifies classroom tools, mini games, creative interactions, and hardware interfaces with native HTML, CSS, and JavaScript. Use when a user wants two or three visual concepts, a playable browser game, a touch-friendly single-file page, a local preview, an optional advanced playground, browser checks, or an Arduino/ESP32 control and data interface.
---

# ChatWeb

Help the user discover the intended feeling and interaction, choose from a small set of professional directions, and create the smallest complete web project that demonstrates it.

ChatWeb is an internal specialist under the ChatMaker parent entry. Keep this Skill independently maintainable, but return user-facing routing and results through ChatMaker.

## Guide the creative choice

- If the request is clear, confirm the desired effect and build without a long interview.
- Start with `chatmaker-web-plan --brief-json '<json>'`. If it returns `clarify`, ask only its one or two plain-language questions and do not recommend styles yet.
- When the planner returns `directions`, recommend its two or three curated beginner directions. For each, describe the visual feeling, primary interaction, suitable scene, and one meaningful tradeoff.
- Only after the user explicitly asks for more, rerun the planner with `--advanced`. Offer `chatmaker-web-playground --advanced ...` only at that point; never create or show the playground as part of the beginner default.

## Workflow

1. Turn the idea, audience/scene, desired feeling or core message, and primary action into the planner brief. Do not move to style selection while the planner still returns `clarify`.
2. Define the primary user action and the visible success, loading, disconnected, and failure states.
3. Present only the planner's two or three beginner directions unless the user explicitly requests the expanded catalog. Record the selected direction or the assumptions used for a direct build.
4. Generate one self-contained HTML file with `chatmaker-web`, with CSS and JavaScript embedded. Split into multiple files only when reuse or project size makes that simpler for the user.
5. Design for phone and classroom use: at least 44 px touch targets, strong contrast, concise labels, visible focus, reduced-motion support, and visible feedback.
   When the user asks for premium, Apple-like or richer motion, read [premium-micro-interactions.md](references/premium-micro-interactions.md). Absorb the interaction pattern into the smallest suitable stack; do not add React or run a component CLI merely to obtain an animation.
6. Start the selected file with `chatmaker-web-preview`. Keep the default `127.0.0.1` binding; use network access only after an explicit request.
7. Verify file loading, browser console errors, the primary interaction, state transitions, and phone-size layout in a real browser.
8. For hardware pages, label simulation visibly. Define the HTTP, serial, Bluetooth, or message contract with `$chatduino` before implementing a real connection.
   For Nano/Uno serial pages, use the versioned JSON-lines contract in `chatmaker.web.device_contract` and start from `examples/chatweb/serial-device-console.html`. Offer this branch only after the hardware goal is clear or the user asks for a page.
9. Only hardware interfaces should read board Wiki guidance, and they should read the `web-and-protocol` section after the exact board identity is known. Independent classroom tools do not load board knowledge.
10. If the page must ship inside firmware, keep one editable HTML source and generate the embedded artifact from it. In this repository, `examples/chatweb/esp32-ap-control.html` is the only editable ESP32 AP page source; regenerate `examples/chatduino/esp32/ap-led-sensor/page_html.h` with `chatmaker-web-embed ... --symbol CHATMAKER_AP_PAGE`.

## Create a mini game

- Use `kind="mini-game"` and read [game-creation-guide.md](references/game-creation-guide.md).
- Ask at most two questions that reveal the desired player feeling, repeated player action, and win or ending condition. Do not begin with engine or genre jargon.
- Offer the three beginner play patterns before visual skins: `reaction-rush`, `dodge-collect`, and `drag-puzzle`.
- Build the smallest complete loop: start, repeated action, immediate feedback, score or progress, ending, and restart.
- Support touch from the first version. Use keyboard controls as an additional path when the game involves movement.
- Games may be creative, entertaining, or educational. Do not turn every game into a quiz or force a classroom wrapper onto a playful idea.
- Keep the beginner default dependency-free and offline-capable. Consider p5play or Phaser only after the requested mechanics exceed the native templates.

Read [web-verification-contract.md](references/web-verification-contract.md) before testing or reporting completion.

## Boundaries

- Support independent classroom tools and creative pages as well as hardware interfaces.
- Treat mini games as a ChatWeb project kind, not as a disguised classroom poll.
- Independent classroom tools should not load board knowledge.
- Do not introduce React, Vue, a database, login, or cloud deployment in v0.1 unless the accepted project cannot reasonably work without it.
- Do not claim hardware connectivity because a page rendered.
- Do not claim hardware connectivity because the simulation changed to a connected state.
- Do not claim an interaction works from source inspection alone; exercise it in a browser.
- Keep secrets and site credentials out of generated client files.
