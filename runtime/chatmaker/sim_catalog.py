"""The board and component inventory supported by the bundled ChatSim demos."""

from importlib.resources import files
import json


def load_catalog() -> dict:
    return json.loads(files("chatmaker").joinpath("sim_assets", "catalog.json").read_text(encoding="utf-8"))
