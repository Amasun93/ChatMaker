from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile


RELEASE_PATHS = (
    ".github/pull_request_template.md",
    ".github/workflows/ci.yml",
    "CONTRIBUTING.md",
    "LICENSE",
    "README.md",
    "README_EN.md",
    "RELEASE_NOTES.md",
    "pyproject.toml",
    "docs",
    "examples",
    "packs",
    "runtime",
    "scripts",
    "skills",
    "tests",
)
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".playwright-cli"}


def _release_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for relative in RELEASE_PATHS:
        path = root / relative
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(candidate for candidate in path.rglob("*") if candidate.is_file())
    return sorted(
        path
        for path in files
        if not EXCLUDED_PARTS.intersection(path.relative_to(root).parts)
        and not any(part.endswith(".egg-info") for part in path.relative_to(root).parts)
        and path.suffix.casefold() not in {".pyc", ".pyo"}
    )


def build_release(root: Path, output_dir: Path, version: str) -> dict[str, object]:
    root = Path(root).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    package_name = f"ChatMaker-{version}"
    archive = output_dir / f"{package_name}.zip"
    files = _release_files(root)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in files:
            relative = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(f"{package_name}/{relative}", date_time=(2026, 8, 14, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, path.read_bytes(), compresslevel=9)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum = output_dir / f"{archive.name}.sha256"
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    return {
        "success": True,
        "version": version,
        "archive": str(archive),
        "checksum_file": str(checksum),
        "sha256": digest,
        "file_count": len(files),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a deterministic ChatMaker release ZIP.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path("dist"))
    parser.add_argument("--version", default="0.1.0-rc2")
    args = parser.parse_args()
    result = build_release(args.root, args.output, args.version)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
