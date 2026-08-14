# ChatMaker

ChatMaker helps beginners build hardware and native-web projects by talking to an AI workspace such as Codex or WorkBuddy. The conversation is the development interface; Mind+, Arduino CLI, serial tools, and the browser are background tools.

> Product: **ChatMaker** · Hardware module: **ChatDuino** · Core experience: **build by talking**

## Current status

ChatMaker is in foundation development. The following labels are strict:

- **Verified:** the named acceptance check has current evidence.
- **Partially verified:** only explicitly listed gates have evidence.
- **Planned:** structure or intent exists, but the behavior is not implemented or validated.

| Area | Status | Current evidence |
| --- | --- | --- |
| Repository and three Skill structure | Verified | All three Skills pass project validation and Codex `quick_validate.py`. |
| Board/component/recipe data contract | Verified | Twelve automated contract tests and the project doctor pass; hardware facts remain unreviewed. |
| Nano Mind+ adapter migration | Planned | Existing repository remains separate and unchanged. |
| Uno and ESP32 compile/upload | Planned | No current hardware evidence in this repository. |
| Native web generation and preview | Planned | Skill workflow only. |
| Codex and WorkBuddy installation | Planned | Installers do not exist yet. |

## Architecture

```text
chatmaker        routes and keeps the beginner project contract
├─ chatduino     hardware, wiring, compile, upload, serial, physical checks
└─ chatmaker-web native HTML/CSS/JS, local preview, browser checks

shared runtime   deterministic tools used by both AI hosts
data packs       boards, components, recipes, and evidence gates
```

## Development checks

```powershell
python -m pip install -e .
python -m unittest discover -s tests -v
python runtime/doctor.py
python scripts/validate_skills.py
```

The implementation plan is in [docs/plans/2026-08-14-chatmaker-v0.1-implementation.md](docs/plans/2026-08-14-chatmaker-v0.1-implementation.md).

## License

Apache-2.0. See [LICENSE](LICENSE).
