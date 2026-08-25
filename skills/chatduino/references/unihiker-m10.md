# UNIHIKER M10 beginner workflow

Use this reference only after the printed board identity is confirmed as **UNIHIKER M10**. K10 is a different MCU board; do not reuse M10 Debian, Jupyter, OpenCV device, or full-Python instructions for it.

## What ChatMaker supports in this phase

- A complete M10 Python project folder rather than an isolated code fragment.
- Python 3.7-compatible source checks through `chatmaker-unihiker`.
- 240×320 screen-aware UI guidance, relative asset paths, and safe camera cleanup.
- Mind+ Python, built-in Jupyter, VS Code, IDLE, Thonny, or SSH as user-selected deployment paths.
- Honest separation between source checks, synchronization, board execution, peripheral behavior, and physical effect.

This phase does not automate SSH credentials, install or upgrade the board image, stop unrelated Python processes, or claim K10 support.

## Cloud credentials: replace internal values before delivery

If the project does not call a cloud model, speech service, or other authenticated API, tell the learner clearly: **this project does not need an API Key**. Do not add empty credential forms to an offline project.

If a cloud service is used, never copy a course, company, teacher, or internal-project credential into the generated project. Before delivery, tell the user all of the following in plain language:

1. The exact field or environment variable that must be replaced.
2. What kind of credential the account owner should put there.
3. The official console where that credential is created or viewed.
4. That `config.example.yaml` stays empty, while the real value belongs in an untracked `config.yaml` or environment variable.

Retrieve the current built-in reminder with:

```powershell
chatmaker-unihiker --request-json '{"action":"credential_help","provider":"aliyun-dashscope"}'
```

Supported provider IDs are `aliyun-dashscope`, `aliyun-qwen-omni`, `volcengine-ark`, `volcengine-openspeech`, and `baidu-tts`. Use only the provider actually selected for the project.

For example, a Qwen project should say: “把私有 `config.yaml` 中的 `aliyun.dashscope.api_key` 换成你自己的阿里云百炼 API Key；在 https://bailian.console.aliyun.com/cn-beijing#/api-key 获取。公开的 `config.example.yaml` 保持空字符串。” Do not ask the user to paste the secret into chat, screenshots, an Issue, or a public repository.

A key stored on an M10 can still be read by someone who controls the device. For a classroom or shared board, do not distribute the teacher's main-account key. Prefer a teacher-controlled proxy, or a dedicated low-permission, low-quota, revocable key whose loss has limited impact.

When a provider has multiple credential fields, keep them together: Qwen-Omni's key must match its endpoint; Volcengine speech needs the App Key and Access Token from the same enabled service; Baidu TTS needs the App ID, API Key, and Secret Key from the same speech application.

## Project shape

Deliver at least:

```text
project/
  main.py
  requirements.txt
  config.example.yaml
  assets/              # only when the project has media files
```

Locate resources with `Path(__file__).resolve().parent`. Never store real account keys in code or the example configuration.

The Debian 10 system interpreter is Python 3.7 by default. Avoid `match/case`, `list[str]`, and `X | None`; use `typing.List` and `typing.Optional` when annotations are needed. A newer pyenv interpreter has a separate package environment, so changing Python versions does not prove that `unihiker`, `pinpong`, OpenCV, or other dependencies remain installed.

## Screen and peripheral rules

- Design the built-in display for 240×320 rather than a desktop window.
- Prefer `unihiker.GUI`, an officially supported full-screen OpenCV path, board buttons/touch, or fixed headless parameters.
- For a camera, verify a real UVC/V4L2 device, handle failed reads, and always call `release()`.
- For audio, verify the actual ALSA output device and provide a visible fallback; the buzzer is not a WAV speaker.
- Confirm the exact connector and signal voltage before assigning GPIO, I2C, SPI, or UART pins. A peripheral powered from 5 V does not prove its signal is safe for 3.3 V logic.
- When M10 and another controller work together, define transport, direction, message format, timeout, and loss-of-link behavior before generating either side.

## Source check

Run:

```powershell
chatmaker-unihiker --request-json '{"action":"check_project","project":"<project-folder>"}'
```

The checker validates the entry point, Python 3.7 grammar, common incompatible annotations, embedded secrets, machine-specific paths, desktop-only OpenCV calls, camera cleanup, and dependency-file presence. When a known provider variable contains a literal secret, the result also includes the exact replacement fields and official acquisition link. A successful result proves only `source_checked`; it does not prove that the project was copied to the board or ran there.

## Deployment and evidence

1. Confirm M10 identity and the selected connection method in Mind+ or the local classroom configuration.
2. Synchronize the entire project folder, including assets and example configuration.
3. On the M10, inspect the active Python version and required imports before installing anything.
4. Run manually and capture the first useful screen or log state.
5. Verify each used peripheral separately. Camera projects should sustain a representative read loop and release the device cleanly.
6. Only after manual runs are stable should the user choose whether to configure auto-start. Auto-start must handle display readiness, device delays, termination, and logs.

Report these gates separately: project generated, source checked, synchronized, process started, runtime log observed, peripheral interaction observed, and physical effect confirmed.

## Official sources reviewed

- M10 product specification: https://www.dfrobot.com/product-2691.html
- M10 development entry points: https://www.unihiker.com/wiki/get-started
- Debian 10 and default Python 3.7 guidance: https://www.unihiker.com/wiki/Troubleshooting/How_to_Install_Multiple_Python_Versions_on_Unihiker
- K10 platform separation: https://www.unihiker.com/wiki/K10/get-started
