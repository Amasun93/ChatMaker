"""Rebuild ChatMaker's redistributable CJK font subset.

The input is the pinned Adobe Source Han Sans SC Regular font.  The output is
renamed because "Source" is a Reserved Font Name under SIL OFL 1.1.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from fontTools import subset
from fontTools.ttLib import TTFont


UPSTREAM_COMMIT = "a4f7cf94edfb9d7ffbdfc4841de276358bd7e0f2"
UPSTREAM_URL = (
    "https://raw.githubusercontent.com/adobe-fonts/source-han-sans/"
    f"{UPSTREAM_COMMIT}/OTF/SimplifiedChinese/SourceHanSansSC-Regular.otf"
)
UPSTREAM_SHA256 = "f1d8611151880c6c336aabeac4640ef434fa13cbfbf1ffe82d0a71b2a5637256"
FAMILY_NAME = "ChatMaker CJK Sans"
POSTSCRIPT_NAME = "ChatMakerCJKSans-Regular"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def subset_codepoints() -> set[int]:
    """Return printable ASCII plus every character defined by GB2312."""
    codepoints = set(range(0x20, 0x7F))
    for lead in range(0xA1, 0xF8):
        for trail in range(0xA1, 0xFF):
            try:
                value = bytes((lead, trail)).decode("gb2312")
            except UnicodeDecodeError:
                continue
            codepoints.update(ord(character) for character in value)
    return codepoints


def _rename_font(font: TTFont) -> None:
    names = font["name"]
    renamed_ids = {1, 2, 3, 4, 5, 6, 16, 17, 18, 21, 22, 25}
    names.names = [record for record in names.names if record.nameID not in renamed_ids]
    values = {
        1: FAMILY_NAME,
        2: "Regular",
        3: "ChatMaker CJK Sans Regular 1.000",
        4: "ChatMaker CJK Sans Regular",
        5: "Version 1.000",
        6: POSTSCRIPT_NAME,
        16: FAMILY_NAME,
        17: "Regular",
    }
    for name_id, value in values.items():
        names.setName(value, name_id, 3, 1, 0x0409)
        names.setName(value, name_id, 1, 0, 0)

    if "CFF " in font:
        cff = font["CFF "].cff
        cff.fontNames = [POSTSCRIPT_NAME]
        top = cff.topDictIndex[0]
        top.FamilyName = FAMILY_NAME
        top.FullName = f"{FAMILY_NAME} Regular"


def build_subset(source: Path, output: Path, metadata: Path) -> dict[str, object]:
    source = source.resolve()
    if _sha256(source) != UPSTREAM_SHA256:
        raise ValueError("unexpected_source_font_sha256")

    options = subset.Options()
    options.layout_features = ["*"]
    options.name_IDs = list(range(0, 26))
    options.name_languages = ["*"]
    options.notdef_glyph = True
    options.notdef_outline = True
    options.recommended_glyphs = True
    options.glyph_names = True
    options.hinting = True

    font = TTFont(source, recalcTimestamp=False)
    codepoints = subset_codepoints()
    worker = subset.Subsetter(options=options)
    worker.populate(unicodes=sorted(codepoints))
    worker.subset(font)
    _rename_font(font)
    if "head" in font:
        font["head"].created = 2082844800
        font["head"].modified = 2082844800

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".otf", delete=False) as handle:
        temporary = Path(handle.name)
    try:
        font.save(temporary, reorderTables=True)
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
        font.close()

    result: dict[str, object] = {
        "schema_version": 1,
        "family_name": FAMILY_NAME,
        "coverage": "Printable ASCII and all characters defined by GB2312",
        "unicode_count": len(codepoints),
        "license": "SIL Open Font License 1.1",
        "license_file": "OFL-1.1.txt",
        "upstream": {
            "repository": "adobe-fonts/source-han-sans",
            "commit": UPSTREAM_COMMIT,
            "url": UPSTREAM_URL,
            "filename": "SourceHanSansSC-Regular.otf",
            "sha256": UPSTREAM_SHA256,
        },
        "asset": {
            "filename": output.name,
            "size": output.stat().st_size,
            "sha256": _sha256(output),
        },
    }
    metadata.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    default_assets = root / "runtime" / "chatmaker" / "cad" / "assets"
    parser = argparse.ArgumentParser(description="Build the bundled ChatMaker CJK font subset.")
    parser.add_argument("source", type=Path, help="Pinned SourceHanSansSC-Regular.otf")
    parser.add_argument("--output", type=Path, default=default_assets / "ChatMakerCJK-Regular.otf")
    parser.add_argument("--metadata", type=Path, default=default_assets / "ChatMakerCJK-Regular.json")
    args = parser.parse_args()
    print(json.dumps(build_subset(args.source, args.output, args.metadata), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
