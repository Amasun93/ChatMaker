"""Build one board Knowledge pack directly from governed repository sources."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from chatmaker.installers.pack_artifact import PackArtifactError, build_pack  # noqa: E402


def _page_text(path: Path, board_id: str, section_id: str) -> str:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError(f"knowledge_page_frontmatter_missing:{path}")
    raw, body = text[4:].split("\n---\n", 1)
    metadata = yaml.safe_load(raw)
    if (
        not isinstance(metadata, dict)
        or metadata.get("board_id") != board_id
        or metadata.get("section_id") != section_id
    ):
        raise ValueError(f"knowledge_page_identity_mismatch:{path}")
    clean_body = body.lstrip("\n")
    return f"---\n{raw}\n---\n{clean_body}"


def build_board_pack(root: Path, board_id: str, version: str, output: Path) -> dict:
    root = root.resolve()
    index_path = root / "knowledge" / "boards" / f"{board_id}.yaml"
    index_text = index_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    index = yaml.safe_load(index_text)
    if not isinstance(index, dict) or index.get("board_id") != board_id:
        raise ValueError("knowledge_index_identity_mismatch")
    sections = index.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ValueError("knowledge_index_sections_missing")
    pack_ids = {item.get("pack_id") for item in sections if isinstance(item, dict)}
    if len(pack_ids) != 1 or not isinstance(next(iter(pack_ids), None), str):
        raise ValueError("knowledge_index_pack_id_invalid")
    pack_id = next(iter(pack_ids))

    with tempfile.TemporaryDirectory(prefix=f"chatmaker-{board_id}-pack-") as temporary:
        staging = Path(temporary) / "knowledge"
        section_root = staging / "sections"
        section_root.mkdir(parents=True)
        (staging / "index.yaml").write_text(index_text, encoding="utf-8", newline="\n")
        for item in sections:
            section_id = item.get("section_id") if isinstance(item, dict) else None
            if not isinstance(section_id, str):
                raise ValueError("knowledge_index_section_id_invalid")
            source = root / "knowledge_sources" / "published" / "boards" / board_id / f"{section_id}.md"
            page = _page_text(source, board_id, section_id)
            (section_root / f"{section_id}.md").write_text(page, encoding="utf-8", newline="\n")
        result = build_pack(
            Path(temporary),
            output,
            pack_id=pack_id,
            pack_version=version,
            board_id=board_id,
            core_minimum="0.1.0",
            core_maximum_exclusive="0.2.0",
        )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a board Knowledge pack from governed sources.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--board-id", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = build_board_pack(args.root, args.board_id, args.version, args.output)
    except (OSError, ValueError, PackArtifactError) as exc:
        result = {"success": False, "error": type(exc).__name__, "detail": str(exc)}
    else:
        result = {"success": True, **result}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
