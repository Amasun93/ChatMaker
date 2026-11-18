---
name: chatduino
description: Act as a beginner hardware creative partner for Arduino Uno, classic Nano, ESP32, micro:bit V2, Starcore, and UNIHIKER M10 projects from an AI workspace. Use for board identification, wiring, complete Arduino/C++ or Python projects, environment discovery, compile/HEX-package/upload checks, serial/runtime observation, and evidence-based physical verification. Do not use for 3D modeling or unsupported board variants.
---

# ChatDuino

Help the user turn an effect or rough idea into a safe physical project without treating a successful command as proof that the physical result happened.

ChatDuino is an internal specialist under the ChatMaker parent entry. Keep this Skill independently maintainable, but return user-facing routing and results through ChatMaker.

## Be a hardware creative partner

- If the user knows the desired effect, avoid a technical questionnaire and move to a safe design.
- If the idea is vague, ask one or two observable questions and offer two or three achievable hardware concepts.
- Explain what each concept does before discussing board IDs, libraries, or protocols.
- Keep professional implementation work internal unless a choice changes cost, safety, or the visible effect.
- 照片不是必需条件。用户说不出模块名称时，每轮只问 1-2 个容易观察的问题，例如针脚数量、丝印、外形和用途。

## Workflow

For classroom projects, save complete source and continue through the board's documented local tools. Use `chatmaker-hardware --request-file project.json` (or `--request-json -` via stdin) with the exact `board_id`, source, confirmed identity and optional serial marker. On Windows x64 and supported Macs this covers Uno R3, classic Nano, Mega 2560, DOIT/Nova, the documented Espressif C3/C6/S3 DevKits and Waveshare S3 V1/V2. On Windows x64 it also covers Starcore v4.2.2. Use standard Arduino libraries for new AVR and ESP32 projects and the board's pinned libraries for Starcore. See `docs/verification/workbuddy-retest-macos.md` for the supported Mac profiles. micro:bit uses its documented HEX route.

For domestic classroom networks, prefer the checked-in Chinese vendor sources and the school's HTTPS mirror. If the teacher sets `CHATMAKER_DOWNLOAD_POLICY=domestic-only`, do not try GitHub fallbacks; report the missing domestic artifact and point to the verified offline cache/mirror path. Never replace a pinned archive with an unreviewed proxy.

1. For wiring guidance, identify the board and module by their printed labels and checked references. For firmware work with a connected but unknown MCU board, resolve wiring safety concerns before using the local `chatmaker-board-identify` CLI. A 临时识别程序 is allowed only after a 完整备份 is verified; always restore and verify the original program afterward. If electronic evidence still overlaps, tell the user where to look for the model/version and then request 正反面照片 if they cannot tell. Keep USB IDs, I2C addresses and registers out of the beginner-facing explanation.
2. Read the matching records under `packs/boards`, `packs/components`, and `packs/recipes`. Use `chatmaker-catalog` with `search` and `get` when available, or read the matching source files directly. For an onboard-hardware question, search the board name together with the hardware term (for example, `星核板 蜂鸣器`), keep a matching board result ahead of generic external modules, and continue to its Knowledge index. Treat unverified records as leads, not facts.
   For one of the 23 self-developed modules, first use `list_modules`, then `module_guide` or `project_task`. Do not treat the seven modules with compiled classroom recipes as the complete module range. All 23 are `guidance_ready`, but code and fixed wiring still depend on `capability_gates.programming` and `capability_gates.wiring`. Keep conditional protocols, version checks, missing measurements, and every `blocked_fact` visible; `not_applicable` means explain safe use without inventing an Arduino program. Historical owner-confirmed use does not prove a current compile, upload, physical effect, or mechanical fit.
3. After the exact board identity is confirmed, use its safety and pin references. Read `identify-and-safety` and `pins-and-electrical`. For firmware work also read `toolchains-and-upload`. Run `chatmaker-knowledge --request-json '{"action":"section","board_id":"<exact-board-id>","consumer":"chatduino","section_id":"identify-and-safety","auto_install":false}'` and substitute the requested section. For wiring-only questions or when a Wiki chapter is unavailable, use the exact board record and available source references directly. If the local record does not cover a pin, check the exact board's pinout or schematic. The current M10 alpha uses [unihiker-m10.md](references/unihiker-m10.md) plus canonical board `unihiker-m10`. For Waveshare ESP32-S3-Touch-LCD-2.8, use its [bundled board reference](references/waveshare-s3-touch-lcd-2-8.md) or the local Wiki; use revision `v2` when the exact 2.8 board and V2 / CST3530 are confirmed.
   Use `auto_install:false` for the first lookup to read local chapters or already installed packs. An installed Skill can use the [bundled board quick start](references/managed-board-quick-start.md) when the full Wiki is unavailable. Tool preparation belongs to the actual build or upload request.
4. Use the [wiring contract](references/beginner-hardware-contract.md) to recommend pins for unwired signals and review the learner's existing connections. Keep a safe, compatible connection even when the example uses a different pin. Resolve electrical and functional conflicts for the selected board and project.
5. When giving connection or rewiring instructions, present one visible disconnected-power `text` wiring block. Add a complete `cpp` block for an Arduino program request, using the accepted wiring. A wiring-only answer ends after the recommendation or review. Do not generate SVG or another wiring graphic unless the user explicitly asks for an image.
6. Use the managed toolchain for the selected board. Run `prepare-environment` if the user asks to prepare it, or use `run` to prepare a missing environment and continue into compilation and upload. Keep the download progress visible on first use. On Windows x64, classic mPython V2.x and mPython V3 also have managed routes. Use an existing Mind+ setup only for the documented compatibility cases. Keep the exact board identity throughout.
7. For MCU boards, compile with the selected board identity and record the command, exit code, and artifact path. For M10, run the Python 3.7 source preflight, then synchronize the complete project and observe a board-side run as separate gates.
8. Upload MCU firmware only when one high-confidence wired port remains. Close serial handles before upload. Do not describe M10 file synchronization as firmware upload.
   For CLIs that require `board_confirmed`, pass `board_confirmed=true` internally only after the user has confirmed the exact printed model or equivalent high-confidence evidence. Never ask a student to type this field or show the raw error code as the whole explanation.
9. Reopen serial after an MCU board returns, or read the M10 process log after launch. Use the `read` or `expect` action in a `chatmaker-serial` JSONL session only for a defined serial workflow; use `write` only when the project defines an input command. Ask for physical confirmation separately.

For existing Windows AVR projects that depend on Mind+ libraries, `chatmaker-avr-project --request-json '<request>'` and the individual board CLIs provide the compatibility route.

ChatMaker Knowledge is shared board guidance, not a second catalog. Use it to read safety, pin, toolchain, and troubleshooting context while preserving canonical facts, IDs, wiring, and verification objects from the checked-in packs.

Read [beginner-hardware-contract.md](references/beginner-hardware-contract.md) whenever producing wiring or code. Read [verification-gates.md](references/verification-gates.md) before any success claim.

## Surface reusable field learning

When an evidence-backed project runs a new or previously unsupported module, corrects missing or wrong guidance, or proves a reusable wiring, library, toolchain, or hardware workaround, return a `knowledge-contribution candidate` to the ChatMaker parent. Include the exact board and module markings, the final working method, the pitfall, and the highest evidence state reached. Do not mark a guess, compilation-only assumption, or unexplained one-off success as reusable knowledge.

Do not publish the Issue from the internal specialist. ChatMaker asks the user once, drafts a privacy-clean contribution only if they agree, and requires explicit confirmation before any public submission or attachment upload.

## UNIHIKER M10

Read [unihiker-m10.md](references/unihiker-m10.md) before generating or checking an M10 project.

- Confirm the printed model is M10. K10 is a separate MCU board and is not supported by this route yet.
- Deliver a complete Python project folder and keep it compatible with the active board interpreter; Debian 10 uses Python 3.7 by default.
- Run `chatmaker-unihiker --request-json '{"action":"check_project","project":"<project-folder>"}'` before any board-side run.
- When the M10 project uses a cloud model or speech API, run `chatmaker-unihiker --request-json '{"action":"credential_help","provider":"<provider-id>"}'` and tell the user the exact private field, credential type, and official acquisition page. Public examples stay empty and real keys never enter chat or Git.
- The source checker does not prove synchronization, imports on the board, process start, screen output, camera/audio behavior, network access, GPIO behavior, or physical effect.
- Do not install packages, change Python versions, configure auto-start, or use stored SSH credentials without an explicit user choice.

## Classic Nano

Use `chatmaker-hardware --board-id arduino-nano-classic --action run --sketch <sketch>` and the managed Arduino AVR environment. If the confirmed ATmega328P Nano's bootloader is known, pass `--bootloader new` or `--bootloader old`. With no explicit setting, the managed route tries the new setting first and checks the same device before retrying after a bootloader synchronization failure.

For a classic Arduino Nano ATmega328P, read [nano-beginner-guidance.md](references/nano-beginner-guidance.md) and [nano-teacher-output-contract.md](references/nano-teacher-output-contract.md). Use the shared ChatMaker Nano runtime for environment discovery, compilation, port selection, and upload.

Read [nano-board-and-pins.md](references/nano-board-and-pins.md) and [nano-wiring-and-safety.md](references/nano-wiring-and-safety.md) before assigning pins or power. For a supported module, read [nano-common-module-cards.md](references/nano-common-module-cards.md). Check each include against the managed environment. [nano-mindplus-libraries.md](references/nano-mindplus-libraries.md) and [nano-mindplus-installation.md](references/nano-mindplus-installation.md) apply to existing Mind+ compatibility projects.

- 只有一个高置信度有线 Nano 时才自动选择端口；蓝牙端口必须排除，多个候选必须让用户选择。
- 编译通过且没有检测到硬件时，提示接入 Nano 后自动上传，不等待老师额外确认，也不能报告烧录成功。
- 编译失败时只修改完整程序，最多自动修改并重试 2 次。
- 串口统一使用 `chatmaker-serial` JSONL 会话的 `list/open/read/expect/write/close` 动作。
- 烧录前关闭占用目标串口的会话。旧项目使用 `chatmaker-nano` 兼容入口时，`compile-upload` 会尝试暂停并恢复该入口管理的串口会话。
- 串口没有输出、只出现启动文字或模拟数据，都不能升级为实物效果已验证。

## Arduino Uno Rev3

Use `chatmaker-hardware --board-id arduino-uno-r3` with the managed Arduino AVR environment. Arduino Mega 2560 uses `arduino-mega-2560`. Existing Mind+ projects on Windows use their documented libraries and entry points.

For a confirmed Arduino Uno Rev3 / Genuino Uno with ATmega328P, use the shared ChatMaker Uno runtime rather than the Nano runtime.

- The Windows compatibility entry is `chatmaker-uno --request-json '<request>'`. Mind+ 1.x compiles with `arduino:avr:uno`; Mind+ 2.x compiles with `mindplus:avr:uno`.
- Uno upload uses the board definition's fixed 115200 baud. Never apply the Nano 57600/115200 Bootloader fallback to Uno.
- Reject Bluetooth ports. Auto-select only one confirmed Uno or one remaining wired candidate; require a choice when multiple wired ports remain.
- Keep compile, upload, serial marker, reboot, and visible LED effect as separate evidence gates.

## 星辰板（ATmega328P / CH340）

- Keep product identity `stardust-atmega328p` separate from a generic Nano even though compilation reuses the compatible Nano target.
- Use `chatmaker-stardust --request-json '<request>'`. After the user confirms the physical product identity, pass `board_confirmed=true` internally.
- The verified Stardust bootloader uses 115200. Its upload route must 只尝试已验证的 115200，不先等待 Nano 的 57600 旧 Bootloader 超时。
- For the verified IDMD-0021 OLED, A4 is SDA and A5 is SCL. The checked `DFRobot_SSD1306_I2C` example proves ASCII display only; for Chinese, read [oled-i2c-troubleshooting.md](references/oled-i2c-troubleshooting.md) and choose an AVR-sized font route.

## DOIT ESP32 DEVKIT V1 with ESP-WROOM-32

Read [esp32-doit-devkit-v1.md](references/esp32-doit-devkit-v1.md) before accepting the board identity, assigning pins, or proposing a toolchain.

- `ESP-WROOM-32` is the module label, not proof of the carrier board. Require the DOIT carrier identity before compile or upload.
- The exact target is `esp32:esp32:esp32doit-devkit-v1`. The managed toolchain selects official Arduino-ESP32 `3.3.12` or its approved `3.3.11` fallback.
- Use `chatmaker-esp32 --action <action>` or `--request-file project.json` with the `prepare-environment`, `doctor`, `ports`, `compile`, or `compile-upload` action.
- Complex legacy requests can use `chatmaker-esp32 --request-json -` with standard input; never require inline JSON through a Windows .cmd wrapper.
- Run `prepare-environment` when the managed toolchain is missing. Let ChatMaker select the sources and a verified core for this exact board. Use the target's own toolchain when working on FireBeetle, mPython, DevKitC, S2, S3, or C3.
- A CP210x, CH340, CH9102, or FTDI serial adapter is only a USB-UART clue; it cannot prove which ESP32 carrier board is attached.
- After generating a complete program, use the `compile-upload` action by default. It may upload only after the exact carrier profile is confirmed and one non-Bluetooth wired port remains. If compilation succeeds without hardware, report `awaiting-hardware`; do not claim upload success.
- Upload success proves only that the upload command completed. Keep reboot, serial output, Wi-Fi AP, HTTP exchange, LED behavior, sensor readings, and power-cycle recovery unverified until each is observed.
- Keep official-core discovery, FQBN details, compilation, upload, reboot, serial evidence, AP connectivity, HTTP exchange, and physical effects separate.
- For this repository's AP demo, keep `examples/chatweb/esp32-ap-control.html` as the only editable page source. Regenerate `examples/chatduino/esp32/ap-led-sensor/page_html.h` with `chatmaker-web-embed ... --symbol CHATMAKER_AP_PAGE` before compile; do not hand-edit the generated header.

## IDMC-0001 Starcore v4.2.2

- Automatic recognition must keep Starcore separate from classic mPython boards. ESP32, CH9102F, QMI8658, or an mPython-compatible target cannot confirm Starcore alone; require the exact firmware marker, verified Starcore combination, or the `星核板` and `V4.2.2` markings. If still ambiguous, use the model-location and photo fallback rather than guessing.
- Use `chatmaker-starcore --request-json '<request>'` with the `prepare-environment`, `doctor`, `ports`, `compile`, or `compile-upload` action.
- Always read Starcore `start-here` before choosing a board feature, then read `identify-and-safety` and `pins-and-electrical` for wiring, power, CAN, or multi-module work. v4.2.2 physically includes A/B buttons, a passive buzzer, QMI8658, CH9102F and a CAN transceiver. The mPython-compatible target also exposes `display/rgb/light/sound`, but those are not onboard Starcore hardware; do not promise a screen, RGB pixels, light sensor or microphone without explicit external wiring.
- For onboard acceleration, tilt, shake, motion control, or gesture projects, read Starcore `start-here` and `libraries-and-examples` before asking hardware questions or writing code. The onboard QMI8658 uses Mind+ built-in acceleration blocks, while `MPython.h` provides `mPython.begin()` plus the global `accelerometer`. Do not ask the user to identify the accelerometer, add a LIS2DH12 extension, connect another sensor, or handwrite I2C unless the checked knowledge explicitly reports a different board revision. QMI8658 contains a gyroscope, but the reviewed public object does not expose gyroscope readings; do not label acceleration as angular velocity or invent a gyro API.
- Use `buttonA/buttonB/buttonAB` for the real active-low onboard buttons and `buzz` for the real passive buzzer. Treat P5/P11 as boot-related, P6 as occupied, P7 as affected by `mPython.begin()`'s software WS2812 initialization, P13/P14 as shared with CAN, and P19/P20 as the shared I2C bus.
- Starcore has eight physical I2C sockets on the shared P19/SCL-P20/SDA bus. For a true I2C module, choose a socket marked for the module voltage and insert the complete four-wire cable; keep the adjacent SCL/C and SDA/D pair together and never split it across distant sockets. IDMS-0009 ultrasonic is not I2C: its 2+2 harness is VCC/GND plus TRIG/ECHO, with the reviewed classroom route H/P26 and O/P27.
- The onboard SIT3051TK is a CAN physical layer, not a complete application protocol. Use a CAN API only after the actual bit rate, termination, cable and protocol are known; unknown buses start listen-only and never receive exploratory control frames. Keep backend-specific headers paired with the selected Mind+ environment.
- For Starcore v4.2.2 on Windows x64, use `chatmaker-hardware --board-id idmc-0001-starcore-v4-2-2`. If the environment is absent, `prepare-environment` installs the pinned Arduino CLI, `mindplus:esp32@0.0.1` core, mPython/OLED libraries and the verified device font. Strict domestic mode can reuse an already prepared Starcore environment. Its initial setup still needs the Arduino index and helper tools.
- Existing usable Mind+ 1.8.x or 2.x installations remain compatibility backends. When both Mind+ versions are usable, prefer 2.x with `mindplus:esp32:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none`; 1.8 uses `dfrobot:mpython:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none`. Do not ask a student to switch between usable Mind+ versions.
- Upload only after the user has confirmed the physical board is Starcore v4.2.2 and one unambiguous non-Bluetooth wired port remains.
- After that confirmation, pass `board_confirmed=true` internally. Before application upload, read the 4-byte marker at Flash `0x400000`; write the verified font only when the marker is not `GUIX`, and report `font_checked` separately from `font_asset_written`. If 1500000 baud returns `PermissionError`, retry once at 115200. If it reports `Invalid head of packet`, give the visible action “按住 A 键，短按 RST，松开 RST 后再松开 A 键”，then retry with manual download mode; do not reduce this to “检查数据线”.
- A successful compile or upload does not verify restart, serial output, connected modules, browser exchange, or physical effects.

Read [starcore-classroom-modules.md](references/starcore-classroom-modules.md) before using a WS2812 strip, a three-wire PWM servo, or the IDMM-0007 serial-servo driver with Starcore. WS2812 and SG90 remain canonical common components; do not invent Starcore-owned replacements for them. IDMM-0007 is a different UART driver, and unknown protocol details permit identification and receive-only diagnosis only—never a movement command.

Read [oled-i2c-troubleshooting.md](references/oled-i2c-troubleshooting.md) when an I2C display is blank or Chinese text is requested. Nano and Uno may use a suitable U8g2 font after an address scan and memory check. Starcore IDMC-0001 with Mind+ mPython must instead use the `MPython.h` global `display` object and the Mind+ font-write path documented there; U8g2 is not a Starcore repair.

## 经典掌控板 V2.x

- Use canonical board `mpython-classic-v2x` and read its `start-here`, `identify-and-safety`, and `toolchains-and-upload` pages.
- V2.0, V2.1, V2.2 and V2.3 do not have one universal sensor combination. Use verified probe identities or printed revision markings; never turn an address clue into a chip model.
- On Windows x64 use `chatmaker-mpython --request-json '<request>'` with `prepare-environment`, `doctor`, `ports`, `compile`, `compile-upload`, `reset`, or `serial-read`. The managed path does not require the Mind+ desktop application.
- Upload and reset require an explicit classic mPython V2.x identity confirmation. A unique non-Bluetooth COM port is not identity evidence. `reset` proves only that the control-line sequence ran; `serial-read` proves only the returned bytes.
- Once identity is confirmed, pass `board_confirmed=true` internally. Use the same `GUIX` marker check and conditional `0x400000` font write as Starcore, keeping font check, font write, application upload and physical display evidence separate. A 1500000-baud `PermissionError` may retry once at 115200; keep both attempts in the returned evidence.
- Mind+ 1.8 uses `dfrobot:mpython:mpython:...`; Mind+ 2.0 uses `mindplus:esp32:mpython:...`. Keep their paths and reset settings separate.
- Arduino `MPython.h` and MicroPython `from mpython import *` expose different APIs. The classic MicroPython display object is `oled`; do not copy the 3.0 `display`/RGB565 examples.

## 掌控板 3.0

- Use canonical board `mpython-v3`. It is an ESP32-S3 board with a 320×172 color LCD and a different GPIO map; never compile it as classic mPython or Starcore.
- Use `chatmaker-mpython-v3` with its managed `prepare-environment`, `doctor`, `ports`, `compile` and `compile-upload` actions. Read serial evidence through `chatmaker-serial` or the workflow's `expected_serial_marker`. Independent compilation is recorded; physical upload/display remain unverified until actually tested. Never substitute a classic target.
- Its MicroPython display object is `display`, and `light.read()` reports lux. Preserve these semantic differences when generating web or hardware code.
- A temporary probe remains subject to the same backup, restore, and verification gates; no restored program means no completed identification.

## BBC micro:bit V2.x

- Use canonical board `microbit-v2`. Confirm V2.x; V1 uses a different target MCU and is not part of this route.
- Use `chatmaker-microbit --request-json '<request>'` with `prepare-environment`, `doctor`, `package-hex`, `volumes`, or `flash`.
- The first layer pins official MicroPython V2 `2.1.1` and `@microbit/microbit-fs@0.10.0`. `package-hex` checks Python syntax and packages `main.py` into the fixed runtime. Call this `source_checked` and `hex_packaged`, not native compilation.
- Upload only to a uniquely selected volume whose real Windows label is `MICROBIT`, whose `DETAILS.TXT` exists, and whose interface version identifies V2. Reject ordinary USB disks, `MAINTENANCE`, V1 interfaces and ambiguous multiple targets.
- A completed copy only proves the DAPLink write command returned. Keep `FAIL.TXT`, re-enumeration, 115200 CDC serial, power-cycle recovery, LED/buttons and other physical effects separate.
- Without a physical board, finish at the source/HEX and virtual safety gates. Do not infer real flashing or device behavior from the MakeCode simulator or a temporary directory.

## Safety boundaries

- Keep USB and external power disconnected while wiring.
- Do not guess a module's controller, pinout, interface, or voltage from a generic product name.
- Do not power motors, pumps, long LED strips, or other high-current loads directly from a GPIO pin.
- Do not use ESP32 5 V logic assumptions; verify the exact variant and 3.3 V constraints.
- Stop before upload when ports, board identity, or bootloader strategy remain ambiguous.

## Waveshare ESP32-S3-Touch-LCD-2.8

Read [waveshare-s3-touch-lcd-2-8.md](references/waveshare-s3-touch-lcd-2-8.md). Use its exact board ID and explicit V1/V2 revision with `chatmaker-hardware`; its independent adapter is `chatmaker-waveshare-s3`. Do not use the DOIT ESP32 target or infer the carrier/revision from a USB identifier. Its source reference is available before a signed Knowledge package; do not request a nonexistent signed pack.
