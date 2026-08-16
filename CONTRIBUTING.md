# Contributing to ChatMaker

ChatMaker accepts focused changes that make beginner hardware or native-web creation safer, clearer, or more reliable.

## Before changing a record

- Confirm the exact board, module controller, interface, voltage, and visible pin labels.
- Cite a manufacturer, official project, datasheet, or maintained library source.
- Keep `source_reviewed`, `code_compiled`, `firmware_uploaded`, and `physical_effect_verified` separate.
- Never mark upload or physical effect as verified from compilation alone.

## Before opening a pull request

```powershell
python -m pip install -e .
python -m unittest discover -s tests -v
python runtime/doctor.py --packs
python scripts/validate_skills.py
git diff --check
```

Add a failing behavior test before changing runtime behavior. For a new component or recipe, follow [the pack format](docs/contributing/pack-format.md) and include a real example file. For a detailed board page, follow the [LLMWiki format](docs/contributing/llmwiki-format.md), complete the [knowledge-source pipeline](docs/contributing/knowledge-source-pipeline.md), and keep canonical YAML out of the optional pack. For a visual change, include the tested viewport, interaction result, and console error count.

Official `.cmpack` URLs must point to the exact commit that already contains those bytes. Sign only with the existing external key after its public identity matches the checked-in anchor. Never commit credentials or create/replace a release key. `chatmaker-pack` alone manages optional knowledge; Codex and WorkBuddy installers remain host-only and reversible.

Do not commit build caches, serial-port guesses, credentials, copied third-party sites, or evidence that belongs to another board variant.
