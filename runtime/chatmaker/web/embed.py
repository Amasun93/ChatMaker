from __future__ import annotations

import argparse
from pathlib import Path
import re


def _raw_delimiter(html: str) -> str:
    candidates = ["CHATMAKER_PAGE", *(f"CM_PAGE_{index}" for index in range(1, 1000))]
    for candidate in candidates:
        if f"){candidate}\"" not in html:
            return candidate
    raise ValueError("unable_to_find_safe_cpp_raw_string_delimiter")


def render_cpp_header(html: str, *, symbol: str) -> str:
    if re.fullmatch(r"[A-Z][A-Z0-9_]*", symbol) is None:
        raise ValueError("invalid_cpp_symbol")
    if "\0" in html:
        raise ValueError("html_contains_nul")
    delimiter = _raw_delimiter(html)
    return (
        "#pragma once\n\n"
        "#include <Arduino.h>\n\n"
        "// Generated from a ChatWeb HTML source. Regenerate instead of editing this file.\n"
        f"const char {symbol}[] PROGMEM = R\"{delimiter}({html}){delimiter}\";\n"
        f"constexpr size_t {symbol}_LENGTH = sizeof({symbol}) - 1;\n"
    )


def embed_html_file(source: Path, output: Path, *, symbol: str) -> Path:
    source = Path(source)
    output = Path(output)
    html = source.read_text(encoding="utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(render_cpp_header(html, symbol=symbol))
    return output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Embed one self-contained ChatWeb HTML file in a C++ PROGMEM header."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--symbol", required=True)
    args = parser.parse_args()
    generated = embed_html_file(args.source, args.output, symbol=args.symbol)
    print(generated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
