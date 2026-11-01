"""Prepare English sensor names for tests using a Core Git installation."""

import json
from pathlib import Path

import homeassistant

sensor = Path(homeassistant.__file__).parent / "components" / "sensor"
translation = sensor / "translations" / "en.json"
if not translation.exists():
    strings = json.loads((sensor / "strings.json").read_text())
    names = {
        key: {
            "name": value["name"].replace(
                "[%key:component::sensor::title%]", strings["title"]
            )
        }
        for key, value in strings["entity_component"].items()
        if "name" in value
    }
    translation.parent.mkdir(exist_ok=True)
    translation.write_text(json.dumps({"entity_component": names}))
