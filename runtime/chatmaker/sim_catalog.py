"""The board and component inventory supported by the bundled ChatSim demos."""

from importlib.resources import files
import json

ASSETS = files("chatmaker").joinpath("sim_assets")
STARCORE_BOARD = "idmc-0001-starcore-v4-2-2"
LIBRARY_IDS = ("starcore", "arduino", "esp32")


def load_starcore_modules() -> list[dict]:
    return json.loads(ASSETS.joinpath("starcore-modules.json").read_text(encoding="utf-8"))


def load_catalog() -> dict:
    catalog = json.loads(ASSETS.joinpath("catalog.json").read_text(encoding="utf-8"))
    interactive = {part for demo in catalog["demos"] for part in demo["parts"]}
    modules = load_starcore_modules()
    for module in modules:
        part = module["id"]
        catalog["parts"][part] = {
            "name": f'{module["code"]} {module["name"]}',
            "availability": "interactive" if part in interactive else "reference",
            "appearance": "starcore-components.js",
            "art": module["art"],
            "catalog_id": part,
        }
    starters = catalog.pop("starter_parts")
    catalog["libraries"] = {
        "starcore": {"board": STARCORE_BOARD, "boards": [STARCORE_BOARD], "parts": [part["id"] for part in modules]},
        "arduino": {"board": "arduino-uno-r3", "boards": ["arduino-uno-r3"], "parts": starters},
        "esp32": {"board": "esp32-devkit-v1", "boards": ["esp32-devkit-v1", "waveshare-esp32-s3-touch-lcd-2-8"],
                  "parts": starters},
    }
    return catalog
