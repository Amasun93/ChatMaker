from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.installers.pack_artifact import PackArtifactError, build_pack  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build a deterministic ChatMaker Knowledge pack whose payload is "
            "knowledge/index.yaml plus knowledge/sections/*.md."
        )
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pack-id", required=True)
    parser.add_argument("--pack-version", required=True)
    parser.add_argument("--board-id", required=True)
    parser.add_argument("--core-minimum", required=True)
    parser.add_argument("--core-maximum-exclusive", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        build_pack(
            args.source,
            args.output,
            pack_id=args.pack_id,
            pack_version=args.pack_version,
            board_id=args.board_id,
            core_minimum=args.core_minimum,
            core_maximum_exclusive=args.core_maximum_exclusive,
        )
    except PackArtifactError as exc:
        print(f"build_pack_failed: {exc.code}: {exc.reason}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
