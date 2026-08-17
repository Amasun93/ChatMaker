from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from . import nano_mindplus


EXAMPLE_NAMES = (
    "blink",
    "dht11-serial",
    "lcd1602-i2c-hello",
    "light-led",
    "oled-light",
    "oled-dashboard",
    "potentiometer-led",
    "relay-control-side",
    "rgb-led-cycle",
    "servo-button",
    "ultrasonic-buzzer",
    "ws2812-one-pixel",
)


def compile_examples(
    example_root: Path,
    *,
    context: dict[str, Any] | None = None,
    discover_fn: Callable[[], list[dict[str, Any]]] = nano_mindplus.discover_installations,
    compile_fn: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] = nano_mindplus.compile_result,
) -> dict[str, Any]:
    root = Path(example_root).expanduser().resolve()
    selected = context
    if selected is None:
        decision = nano_mindplus.choose_environment(discover_fn())
        selected = nano_mindplus._selected_context(decision)
        if selected is None:
            return {
                "success": False,
                "error": "mindplus_not_installed_or_toolchain_missing",
                "compiled": 0,
                "passed": 0,
                "failed": 0,
                "results": [],
                "environment": decision,
            }

    results: list[dict[str, Any]] = []
    for name in EXAMPLE_NAMES:
        sketch = root / name / f"{name}.ino"
        if not sketch.is_file():
            result: dict[str, Any] = {
                "success": False,
                "error": "example_sketch_not_found",
                "sketch": str(sketch),
            }
        else:
            result = compile_fn(
                selected,
                {
                    "sketch": str(sketch),
                    "project_name": name,
                    "timeout": 600,
                },
            )
        results.append({"name": name, **result})

    passed = sum(bool(result.get("success")) for result in results)
    failed = len(results) - passed
    return {
        "success": failed == 0,
        "compiled": len(results),
        "passed": passed,
        "failed": failed,
        "backend": selected.get("backend"),
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile the supported Nano examples.")
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args(argv)
    report = compile_examples(args.root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
