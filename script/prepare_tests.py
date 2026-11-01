"""Prepare English entity names for tests using a Core Git installation."""

import json
from pathlib import Path

import homeassistant

for platform in ("sensor", "binary_sensor"):
    component = Path(homeassistant.__file__).parent / "components" / platform
    translation = component / "translations" / "en.json"
    if not translation.exists():
        strings = json.loads((component / "strings.json").read_text())
        names = {
            key: {
                "name": value["name"].replace(
                    f"[%key:component::{platform}::title%]", strings["title"]
                )
            }
            for key, value in strings["entity_component"].items()
            if "name" in value
        }
        translation.parent.mkdir(exist_ok=True)
        translation.write_text(json.dumps({"entity_component": names}))
