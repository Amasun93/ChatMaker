"""Build ChatSim's portable Starcore inventory from the component and mechanical cards."""

import argparse
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "runtime/chatmaker/sim_assets/starcore-modules.json"
ART = {
    "IDMD-0021": "oled",
    "IDMS-0001": "button",
    "IDMS-0002": "switch",
    "IDMS-0003": "knob",
    "IDMS-0004": "encoder",
    "IDMS-0005": "light",
    "IDMD-0001": "rgb",
    "IDMS-0008": "dht11",
    "IDMS-0009": "ultrasonic",
    "IDMD-0002": "mp3",
    "IDMS-0036": "accelerometer",
}


def build_library():
    modules = []
    for path in sorted((ROOT / "packs/components").glob("id*-starcore-*.yaml")):
        card = yaml.safe_load(path.read_text(encoding="utf-8"))
        profile_path = ROOT / "knowledge/mechanical/components" / (card["id"] + ".json")
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        outline = profile["outline"]
        mounting = profile["mounting"]
        if outline["shape"] != "rectangle" or outline["status"] != "source_reviewed":
            raise ValueError(f"Unsupported outline in {profile_path.name}")
        modules.append({
            "id": card["id"],
            "code": card["hardware_id"],
            "name": card["name"],
            "category": card["category"],
            "size_mm": [outline["width"], outline["depth"]],
            "holes_mm": [[hole["x"], hole["y"]] for hole in mounting["holes"]
                         if hole["status"] == "source_reviewed"],
            "pins": [pin["id"] for pin in card["pins"] if pin["id"] != "CONNECTION"],
            "art": ART.get(card["hardware_id"], "outline"),
        })
    return sorted(modules, key=lambda module: (module["art"] == "outline", module["code"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = json.dumps(build_library(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if TARGET.read_text(encoding="utf-8") != content:
            parser.exit(1, "Starcore library is out of date. Run this script without --check.\n")
    else:
        TARGET.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
