from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
BOARD_ID = "idmc-0001-starcore-v4-2-2"
BOARD_PATH = Path("packs/boards") / f"{BOARD_ID}.yaml"
SELF_TEST_PATH = Path("packs/recipes/starcore-onboard-self-test.yaml")
OLED_RECIPE_PATH = Path("packs/recipes/starcore-idmd-0021-oled-message.yaml")
KNOWLEDGE_INDEX_PATH = Path("knowledge/boards") / f"{BOARD_ID}.yaml"
KNOWLEDGE_TOOLCHAIN_PATH = (
    Path("knowledge_sources/published/boards") / BOARD_ID / "toolchains-and-upload.md"
)
README_PATH = Path("README.md")
INSTALLATION_PATH = Path("docs/installation.md")

README_START = "<!-- starcore-evidence-summary:start -->"
README_END = "<!-- starcore-evidence-summary:end -->"
KNOWLEDGE_START = "<!-- starcore-evidence-summary:start -->"
KNOWLEDGE_END = "<!-- starcore-evidence-summary:end -->"
INSTALL_START = "<!-- starcore-install-evidence:start -->"
INSTALL_END = "<!-- starcore-install-evidence:end -->"


def _load_yaml(root: Path, relative: Path) -> dict[str, Any]:
    value = yaml.safe_load((root / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{relative.as_posix()}: expected a YAML mapping")
    return value


def _gate(record: dict[str, Any], name: str) -> dict[str, Any]:
    gate = record.get("verification", {}).get(name)
    if not isinstance(gate, dict):
        raise ValueError(f"{record.get('id', '<record>')}: missing verification.{name}")
    return gate


def _scoped(items: Any, key: str) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list):
        return {}
    return {
        item[key]: item
        for item in items
        if isinstance(item, dict) and isinstance(item.get(key), str)
    }


def _expect_status(errors: list[str], label: str, gate: dict[str, Any], expected: str) -> None:
    actual = gate.get("status")
    if actual != expected:
        errors.append(f"{label}: expected {expected}, found {actual}")


def _canonical_errors(board: dict[str, Any], self_test: dict[str, Any], oled: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    toolchains = {
        item.get("id"): item.get("status")
        for item in board.get("toolchains", [])
        if isinstance(item, dict)
    }
    for toolchain_id in (
        "chatmaker-managed-starcore",
        "mindplus-1.8-mpython",
        "mindplus-2.0-mpython",
    ):
        if toolchains.get(toolchain_id) != "verified_supported":
            errors.append(f"board.toolchains: {toolchain_id} must be verified_supported")
    selection = board.get("toolchain_selection", {})
    if selection.get("policy") != "reuse-any-usable-installation":
        errors.append("board.toolchain_selection: must reuse any usable Mind+ installation")
    if selection.get("when_none_available") != "prepare-chatmaker-managed-starcore":
        errors.append("board.toolchain_selection: missing managed Starcore preparation route")

    _expect_status(
        errors,
        "board.physical_effect_verified",
        _gate(board, "physical_effect_verified"),
        "not_applicable",
    )
    features = _scoped(board.get("feature_verification"), "feature_id")
    for feature_id in ("qmi8658", "passive-buzzer", "button-a", "button-b"):
        if feature_id not in features:
            errors.append(f"board.feature_verification: missing {feature_id}")
    if "passive-buzzer" in features:
        _expect_status(
            errors,
            "feature.passive-buzzer.physical_effect_verified",
            features["passive-buzzer"]["verification"]["physical_effect_verified"],
            "verified",
        )
    for button_id in ("button-a", "button-b"):
        if button_id in features:
            _expect_status(
                errors,
                f"feature.{button_id}.physical_effect_verified",
                features[button_id]["verification"]["physical_effect_verified"],
                "verified",
            )

    for gate_name in ("code_compiled", "firmware_uploaded", "serial_evidence"):
        _expect_status(errors, f"self-test.{gate_name}", _gate(self_test, gate_name), "verified")
    _expect_status(
        errors,
        "self-test.physical_effect_verified",
        _gate(self_test, "physical_effect_verified"),
        "not_applicable",
    )

    for gate_name in (
        "code_compiled",
        "firmware_uploaded",
        "serial_evidence",
        "display_proxy_evidence",
    ):
        _expect_status(errors, f"oled.{gate_name}", _gate(oled, gate_name), "verified")
    _expect_status(
        errors,
        "oled.physical_effect_verified",
        _gate(oled, "physical_effect_verified"),
        "verified",
    )
    return errors


def _readme_summary() -> str:
    return (
        "| 星核板独立 CLI | Beta P1 实测 | ChatMaker 管理的隔离工具链已完成准备、地震预警站编译、COM4 上传、硬复位和 115200 串口验证，不要求安装 Mind+ 应用。已有 Mind+ 1.8 或 2 仍可作为兼容后端。此前用户确认中文 OLED、防闪、蜂鸣器与 A/B 键均正常；本轮只重新验证了编译、上传和串口数据。 |"
    )


def _knowledge_index_summary() -> str:
    return (
        "优先使用 ChatMaker 管理的独立 CLI；无需安装 Mind+ 应用。Mind+ 1.8 和 2 仍可作为兼容后端。独立链路已完成地震预警站编译、COM4 上传、硬复位和 115200 串口验证。"
    )


def _knowledge_block() -> str:
    return "\n".join(
        (
            "## 当前结构化证据摘要",
            "",
            "ChatMaker 管理的独立 CLI 是星核板首选后端；它在隔离目录中使用固定 Arduino CLI、`mindplus:esp32@0.0.1` 核心和六个校验过的 mPython/OLED/中文字库，不要求安装 Mind+ 应用。Mind+ 1.8 和 2 仍是可用的兼容后端，两者都有时兼容路线默认选择 2。",
            "",
            "2026-08-26，独立链路用桌面地震预警站完成真实编译、COM4 上传、RTS 硬复位和 115200 串口回读，看到 `STARCORE_QUAKE_STATION_UI_V2_READY` 与连续 `QUAKE_DATA`。此前用户已确认中文 OLED、防闪、蜂鸣器、A/B 键和预警效果均正常；本轮没有重新肉眼或听觉确认这些实体效果。",
            "",
            "权威状态读取 `packs/boards/idmc-0001-starcore-v4-2-2.yaml`、`packs/recipes/starcore-onboard-self-test.yaml` 和 `packs/recipes/starcore-idmd-0021-oled-message.yaml`；本段由 `scripts/sync_starcore_evidence.py` 生成。",
        )
    )


def _installation_block() -> str:
    return "\n".join(
        (
            "星核板首选 ChatMaker 管理的独立 CLI，不要求安装 Mind+ 应用。首次执行 `chatmaker-starcore --request-json '{\"action\":\"prepare-environment\"}'` 会在 ChatMaker 自己的目录中下载并校验固定 Arduino CLI、`mindplus:esp32@0.0.1` 核心和六个 mPython/OLED/中文字库。已有 Mind+ 1.8 或 2 仍可作为兼容后端。",
            "",
            "独立链路已用桌面地震预警站完成编译、COM4 上传、硬复位和 115200 串口验证。此前用户确认中文 OLED、防闪、蜂鸣器、A/B 键和预警效果正常；本轮没有重新做肉眼或听觉验收。CAN、断电重启和其他模块继续分别验收。",
        )
    )


def _replace_block(text: str, start: str, end: str, body: str, path: Path) -> str:
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError(f"{path.as_posix()}: expected one generated block")
    before, remainder = text.split(start, 1)
    _, after = remainder.split(end, 1)
    return f"{before}{start}\n{body}\n{end}{after}"


def _replace_index_summary(text: str, summary: str) -> str:
    section_marker = "  - section_id: toolchains-and-upload\n"
    if section_marker not in text:
        raise ValueError(f"{KNOWLEDGE_INDEX_PATH.as_posix()}: missing toolchains section")
    before, remainder = text.split(section_marker, 1)
    next_marker = "  - section_id: components-and-wiring\n"
    section, after = remainder.split(next_marker, 1)
    lines = section.splitlines()
    matches = [index for index, line in enumerate(lines) if line.startswith("    summary: ")]
    if len(matches) != 1:
        raise ValueError(f"{KNOWLEDGE_INDEX_PATH.as_posix()}: expected one toolchain summary")
    lines[matches[0]] = f"    summary: {summary}"
    updated = "\n".join(lines) + "\n"
    return f"{before}{section_marker}{updated}{next_marker}{after}"


def _expected_files(root: Path) -> dict[Path, str]:
    expected: dict[Path, str] = {}
    readme = (root / README_PATH).read_text(encoding="utf-8")
    expected[README_PATH] = _replace_block(
        readme, README_START, README_END, _readme_summary(), README_PATH
    )
    toolchain = (root / KNOWLEDGE_TOOLCHAIN_PATH).read_text(encoding="utf-8")
    expected[KNOWLEDGE_TOOLCHAIN_PATH] = _replace_block(
        toolchain,
        KNOWLEDGE_START,
        KNOWLEDGE_END,
        _knowledge_block(),
        KNOWLEDGE_TOOLCHAIN_PATH,
    )
    installation = (root / INSTALLATION_PATH).read_text(encoding="utf-8")
    expected[INSTALLATION_PATH] = _replace_block(
        installation,
        INSTALL_START,
        INSTALL_END,
        _installation_block(),
        INSTALLATION_PATH,
    )
    index = (root / KNOWLEDGE_INDEX_PATH).read_text(encoding="utf-8")
    expected[KNOWLEDGE_INDEX_PATH] = _replace_index_summary(index, _knowledge_index_summary())
    return expected


def synchronize(root: Path, *, write: bool) -> dict[str, Any]:
    root = root.resolve()
    board = _load_yaml(root, BOARD_PATH)
    self_test = _load_yaml(root, SELF_TEST_PATH)
    oled = _load_yaml(root, OLED_RECIPE_PATH)
    errors = _canonical_errors(board, self_test, oled)
    updated: list[str] = []
    try:
        expected = _expected_files(root)
    except (OSError, UnicodeError, ValueError) as exc:
        errors.append(str(exc))
        expected = {}

    for relative, expected_text in expected.items():
        path = root / relative
        actual = path.read_text(encoding="utf-8")
        requires_lf = relative == KNOWLEDGE_TOOLCHAIN_PATH and b"\r" in path.read_bytes()
        if actual == expected_text and not requires_lf:
            continue
        if write and not errors:
            with path.open("w", encoding="utf-8", newline="\n") as stream:
                stream.write(expected_text)
            updated.append(relative.as_posix())
        else:
            errors.append(f"{relative.as_posix()}: generated Starcore evidence summary is stale")

    stale_patterns = {
        KNOWLEDGE_TOOLCHAIN_PATH: (
            "课堂当前路线使用 Mind+ 1.8",
            "Mind+ 2.0 的 `mindplus:esp32:mpython:...` 是历史路线",
        ),
        Path("knowledge_sources/published/boards")
        / BOARD_ID
        / "libraries-and-examples.md": (
            "实际可听蜂鸣仍保持 `unverified`",
        ),
    }
    for relative, patterns in stale_patterns.items():
        text = (root / relative).read_text(encoding="utf-8")
        for pattern in patterns:
            if pattern in text:
                errors.append(f"{relative.as_posix()}: stale claim remains: {pattern}")

    return {
        "success": not errors,
        "mode": "write" if write else "check",
        "updated": updated,
        "errors": errors,
        "canonical_records": [
            BOARD_PATH.as_posix(),
            SELF_TEST_PATH.as_posix(),
            OLED_RECIPE_PATH.as_posix(),
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate or check Starcore evidence summaries from canonical pack records."
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    result = synchronize(args.root, write=args.write)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
