---
name: chatmaker-web
description: Create and verify beginner-friendly interactive projects with native HTML, CSS, and JavaScript, including local prototypes and ESP32-served control pages. Use when an AI-workspace user wants a touch-friendly page, classroom interaction, local browser preview, browser error checks, or a hardware control interface without React, Vue, authentication, databases, or cloud infrastructure.
---

# ChatMaker Web

Create the smallest complete native-web project that demonstrates the requested interaction.

## Workflow

1. Define the primary user action and the visible success, loading, disconnected, and failure states.
2. Use semantic HTML, readable CSS, and plain JavaScript. Keep the project self-contained unless an external dependency is necessary and approved.
3. Design for phone and classroom use: large touch targets, strong contrast, concise labels, and visible feedback.
4. Start preview on localhost by default. Expose a LAN address only when the user requests another device to connect.
5. Verify file loading, browser console errors, the primary interaction, and state transitions.
6. For ESP32 pages, define the HTTP or message contract with `$chatduino` before implementing either side.

Read [web-verification-contract.md](references/web-verification-contract.md) before testing or reporting completion.

## Boundaries

- Do not introduce React, Vue, a database, login, or cloud deployment in v0.1.
- Do not claim hardware connectivity because a page rendered.
- Do not claim an interaction works from source inspection alone; exercise it in a browser.
- Keep secrets and site credentials out of generated client files.

