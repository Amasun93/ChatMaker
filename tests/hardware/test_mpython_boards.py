from __future__ import annotations

from pathlib import Path

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[2]
CLASSIC_ID = "mpython-classic-v2x"
V3_ID = "mpython-v3"
SECTION_IDS = {
    "start-here",
    "identify-and-safety",
    "pins-and-electrical",
    "toolchains-and-upload",
    "components-and-wiring",
    "libraries-and-examples",
    "web-and-protocol",
    "troubleshooting",
}


def _load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _frontmatter(path: Path):
    text = path.read_text(encoding="utf-8")
    _, raw, body = text.split("---", 2)
    assert body.strip()
    return yaml.safe_load(raw)


def test_two_mpython_generations_are_independent_valid_board_records():
    schema = _load(ROOT / "packs" / "schemas" / "board.schema.yaml")
    validator = jsonschema.Draft202012Validator(schema)
    classic = _load(ROOT / "packs" / "boards" / f"{CLASSIC_ID}.yaml")
    v3 = _load(ROOT / "packs" / "boards" / f"{V3_ID}.yaml")

    validator.validate(classic)
    validator.validate(v3)
    assert classic["mcu"] == "ESP32"
    assert v3["mcu"] == "ESP32-S3"
    assert classic["display"]["resolution"] == "128x64"
    assert classic["display"]["api_object"] == "oled"
    assert v3["display"]["resolution"] == "320x172"
    assert v3["display"]["api_object"] == "display"
    assert classic["id"] != v3["id"]


def test_classic_record_preserves_hardware_revision_sensor_changes():
    board = _load(ROOT / "packs" / "boards" / f"{CLASSIC_ID}.yaml")

    revisions = {item["revision"]: item for item in board["hardware_revisions"]}
    assert revisions["V2.0"]["accelerometer"] == "MSA300"
    assert revisions["V2.1"]["accelerometer"] == "QMI8658C"
    assert revisions["V2.1"]["usb_uart"] == "CH9102"
    assert revisions["V2.2"]["magnetometer"] == "MMC5603NJ"
    assert board["automatic_identification"]["exact_revision_may_require_silkscreen"] is True
    assert board["verification"]["firmware_uploaded"]["status"] == "unverified"


def test_v3_record_keeps_new_pin_and_light_semantics_separate():
    board = _load(ROOT / "packs" / "boards" / f"{V3_ID}.yaml")

    assert board["gpio_map"]["P19"] == 43
    assert board["gpio_map"]["P20"] == 44
    assert board["sensor_semantics"]["light_read_unit"] == "lux"
    onboard = {item["id"] for item in board["onboard_hardware"]}
    assert {"qmi8658c", "mmc5603nj", "ltr-308als-01", "speaker"}.issubset(onboard)
    assert board["toolchains"][0]["status"] == "source_indexed_toolchain_not_installed"


def test_both_boards_publish_the_standard_knowledge_sections():
    for board_id in (CLASSIC_ID, V3_ID):
        index = _load(ROOT / "knowledge" / "boards" / f"{board_id}.yaml")
        assert {item["section_id"] for item in index["sections"]} == SECTION_IDS
        pages = ROOT / "knowledge_sources" / "published" / "boards" / board_id
        for section_id in SECTION_IDS:
            page = _frontmatter(pages / f"{section_id}.md")
            assert page["board_id"] == board_id
            assert page["section_id"] == section_id
