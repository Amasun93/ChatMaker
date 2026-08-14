---
name: chatduino
description: Design, wire, compile, upload, observe, and troubleshoot beginner Arduino Uno, classic Arduino Nano ATmega328P, and ESP32 projects from an AI workspace. Use for board or component identification, safe pin planning, complete Arduino/C++ code, Mind+ or Arduino CLI environment discovery, serial monitoring, and evidence-based physical verification. Do not use for 3D modeling or unsupported board variants.
---

# ChatDuino

Build small hardware projects without treating a successful command as proof that the physical result happened.

## Workflow

1. Identify the exact board variant, controller, USB interface, component labels, supply voltage, and desired effect.
2. Read the matching records under `packs/boards`, `packs/components`, and `packs/recipes` through the shared runtime. Treat unverified records as leads, not facts.
3. Resolve pin, voltage, current, boot, serial, and shared-ground constraints before writing code.
4. Present a visible disconnected-power wiring block, then a complete `cpp` block.
5. Discover an existing Mind+ or Arduino CLI toolchain. Do not install or switch toolchains silently.
6. Compile with the selected board identity and record the command, exit code, and artifact path.
7. Upload only when one high-confidence wired port remains. Close serial handles before upload.
8. Reopen serial after the board returns, inspect expected and failure markers, and ask for physical confirmation.

Read [beginner-hardware-contract.md](references/beginner-hardware-contract.md) whenever producing wiring or code. Read [verification-gates.md](references/verification-gates.md) before any success claim.

## Safety boundaries

- Keep USB and external power disconnected while wiring.
- Do not guess a module's controller, pinout, interface, or voltage from a generic product name.
- Do not power motors, pumps, long LED strips, or other high-current loads directly from a GPIO pin.
- Do not use ESP32 5 V logic assumptions; verify the exact variant and 3.3 V constraints.
- Stop before upload when ports, board identity, or bootloader strategy remain ambiguous.

