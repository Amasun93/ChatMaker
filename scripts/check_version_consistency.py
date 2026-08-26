from __future__ import annotations

import sys
from pathlib import Path
import tomllib

try:
    from packaging.version import Version
except ImportError:
    from pip._vendor.packaging.version import Version


VERSION_FILES = (
    Path("README.md"),
    Path("README_EN.md"),
    Path("WHATS_NEW.md"),
    Path("docs/roadmap.md"),
)
CURRENT_USER_DOCS = VERSION_FILES + (Path("docs/installation.md"),)
REMOVED_RC5_RELEASE_LINK = "github.com/Amasun93/ChatMaker/releases/tag/v0.1.0-rc5"


def public_version(root: Path) -> str:
    metadata = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    version = Version(metadata["project"]["version"])
    if version.pre is None:
        return version.public
    label, number = version.pre
    readable_label = {"a": "alpha", "b": "beta", "rc": "rc"}[label]
    return f"{version.base_version}-{readable_label}.{number}"


def check(root: Path) -> list[str]:
    version = public_version(root)
    errors: list[str] = []
    for relative in VERSION_FILES:
        path = root / relative
        if not path.is_file():
            errors.append(f"missing:{relative.as_posix()}")
        elif version not in path.read_text(encoding="utf-8"):
            errors.append(f"version_missing:{relative.as_posix()}:{version}")
    for relative in CURRENT_USER_DOCS:
        path = root / relative
        if path.is_file() and REMOVED_RC5_RELEASE_LINK in path.read_text(encoding="utf-8"):
            errors.append(f"removed_release_link:{relative.as_posix()}")
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = check(root)
    if errors:
        print("\n".join(errors))
        return 1
    print(f"version_consistent:{public_version(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
