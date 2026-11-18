"""The board and component inventory supported by the bundled ChatSim demos."""

from importlib.resources import files
import json

ASSETS = files("chatmaker").joinpath("sim_assets")
STARCORE_BOARD = "idmc-0001-starcore-v4-2-2"


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
    catalog["libraries"] = {"starcore": {"board": STARCORE_BOARD, "parts": [module["id"] for module in modules]}}
    return catalog
