# Beginner Hardware Output Contract

## Explain the effect

Use two to four everyday sentences: what the project senses, when it decides, and what it changes. Introduce only the technical terms needed for the current step.

## Wiring block

Use the heading `## 🔌 接线说明（先断电）` followed immediately by one `text` block containing:

- `【先断电】`
- `【引脚占用】`
- `【按顺序接线】`
- `【通电前检查】`

Write every connection as `component printed label → board printed label`. Include resistor, external-power, shared-ground, and polarity requirements where relevant.

This text block is the default and complete wiring deliverable. Do not create SVG, Fritzing, or another rendered wiring diagram unless the user explicitly requests an image. If an image is requested, keep the text block as the source of truth.

## Program block

Use the heading `## 💻 完整程序（可整段复制）` followed immediately by one complete `cpp` block. Put adjustable values near the top, choose a safe startup state, and use comments that explain the observable effect.

## Unknown components

Ask one or two observable questions per turn: pin or wire count, printed letters, distinctive shape, wire colors, and intended use. A photo is optional. If controller, interface, or voltage remains ambiguous, provide the next identification step and do not provide potentially destructive wiring.
