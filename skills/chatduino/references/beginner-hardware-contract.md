# Beginner Hardware Output Contract

## Choose or review the connections

Check the exact board model and revision, the module's printed labels and electrical limits, and the features this project uses. Use the board record and pin reference with the module record. Match the board's printed label to its code pin or alias. A bare number can refer to a different pin on another board. Check supply and signal voltage separately, common ground, direction and capabilities such as analog input or PWM, and pins used by the board, libraries, or other modules. Check startup, USB and buses when relevant. I²C devices can share SDA/SCL when their voltage, pull-ups and addresses are compatible.

- **还没接。** Give one suitable set of pins, using an exact board and module recipe when it fits. Prefer free pins that support the signal and leave the project's other features available. Give `模块丝印 → 主控板丝印` for power, ground and each signal. Say why a suggested pin matters only where it helps the learner make the connection.
- **已经接了。** Start with the student's actual connections and the verdict for those lines. On a partially wired project, review the connected lines and recommend pins for the rest. If a pin number or a missing voltage could change the verdict, ask for the specific label or value and give the result for what is known.

Use the board and module records for electrical facts. If an installed Knowledge page calls for confirmation whenever a wire differs from its recipe, check the reported pin using this review flow. Ask for confirmation when a label, capability or safe voltage remains uncertain, and pause the affected line until it is resolved.

Use the relevant verdicts in the review. State the reason and what the learner needs to do for each affected line.

| 结论 | 何时使用 |
| --- | --- |
| 可以保留 | The pin is electrically safe and supports the requested use. Keep it when the recipe shows a different optional pin. |
| 有条件保留 | The connection is electrically safe and a known limitation has little effect on this project. State the condition, the likely symptom if it changes, and a simple way to check when helpful. Let the learner keep the pin or choose a suitable alternative. |
| 需要改线 | The connection is electrically unsafe, the pin cannot do the job, or the conflict affects a feature the learner needs. Give the smallest change, including any required electrical protection. For an unsafe connection, unplug USB and external power before proceeding and resolve the issue before power-on or upload. |
| 待确认 | The available evidence cannot establish a pin's function or safety. Ask for the specific board or module marking, signal-to-pin mapping, or voltage that would resolve it. |

On a confirmed classic Nano, a correctly powered potentiometer with its middle pin on free A1 can stay on A1. On the [classic DOIT ESP32 DevKit V1](esp32-doit-devkit-v1.md), a 3.3 V-powered potentiometer can stay on GPIO25 for analog readings with Wi-Fi off. If the project must read it while Wi-Fi is on, unplug power, move the middle wire to free GPIO34 and update the code. [Espressif's classic ESP32 GPIO reference](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/peripherals/gpio.html#gpio-summary)

Use the accepted wiring in the code and any project pin list. If a wire must move, state the exact move and use that new pin in the program. A review describes the wiring the learner reported and what still needs checking on the bench.

## Explain the effect

For a project explanation, use two to four everyday sentences describing what it senses, when it decides, and what it changes. For a wiring-only question, lead with the suggested connection or the review verdict.

## Wiring block

When giving instructions to connect or move wires, use the heading `## 🔌 接线说明（先断电）` followed immediately by one `text` block containing the following items.

- `【先断电】`
- `【引脚占用】`
- `【按顺序接线】`
- `【通电前检查】`

Write every connection as `component printed label → board printed label`. Include resistor, external-power, shared-ground, and polarity requirements where relevant.

This text block is the default and complete wiring deliverable. Do not create SVG, Fritzing, or another rendered wiring diagram unless the user explicitly requests an image. If an image is requested, keep the text block as the source of truth.

## Program block

For an Arduino program request, use the heading `## 💻 完整程序（可整段复制）` followed immediately by one complete `cpp` block. Put adjustable values near the top, choose a safe startup state, and use comments that explain the observable effect.

## Unknown components

Ask one or two observable questions per turn: pin or wire count, printed letters, distinctive shape, wire colors, and intended use. A photo is optional. If controller, interface, or voltage remains ambiguous, provide the next identification step and do not provide potentially destructive wiring.
