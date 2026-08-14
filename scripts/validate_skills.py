from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.skills import validate_skill_directory  # noqa: E402


def main() -> int:
    errors: list[str] = []
    for skill_dir in sorted(path for path in (ROOT / "skills").iterdir() if path.is_dir()):
        skill_errors = validate_skill_directory(skill_dir)
        if skill_errors:
            errors.extend(skill_errors)
            print(f"[FAIL] {skill_dir.name}")
            for error in skill_errors:
                print(f"  - {error}")
        else:
            print(f"[OK] {skill_dir.name}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

