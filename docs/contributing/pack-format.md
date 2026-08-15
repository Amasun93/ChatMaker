# Contributing Data Packs

Create one YAML file per record under `packs/boards`, `packs/components`, or `packs/recipes`. Use lowercase hyphenated IDs and keep IDs unique across all record kinds.

Run:

```powershell
python runtime/doctor.py --packs
python -m unittest discover -s tests -v
```

A contribution must cite its sources and preserve all four baseline evidence gates. Set any gate to `verified` only with a date and a specific evidence note. Recipes may add extension gates such as `wifi_ap_available` or `http_exchange_verified`, but only when that recipe actually needs the extra runtime proof. Boards and components should not inherit recipe-only extension gates by default. When a recipe references a board or component, that ID must already exist. Two wires may share a board pin only when every connection explicitly sets `shared: true`; this is intended for reviewed buses or power rails, not accidental signal conflicts.

