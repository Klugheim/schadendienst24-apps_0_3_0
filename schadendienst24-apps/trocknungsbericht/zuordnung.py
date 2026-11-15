import json
import re
from pathlib import Path

options = json.loads(Path("/data/options.json").read_text())

def entity(key, domain):
    value = options.get(key, "input_datetime.kwh_reset") if key == "trocknungsbeginn_entitaet" else options[key]
    if not isinstance(value, str) or not re.fullmatch(domain + r"\.[a-z0-9_]+", value):
        raise ValueError(f"Ungültige Entität bei {key}: {value!r}")
    return value

HUMIDITY = [entity(f"th{i}_a_feuchte", "sensor") for i in range(1, 9)]
TEMPERATURE = [entity(f"th{i}_a_temperatur", "sensor") for i in range(1, 9)]
SWITCHES = [entity(f"kanal{i}_schalter", "switch") for i in range(1, 4)]

for entries in (HUMIDITY, TEMPERATURE, SWITCHES):
    if len(entries) != len(set(entries)):
        raise ValueError("Eine Entität wurde mehrfach zugeordnet")

START_ENTITY = entity("trocknungsbeginn_entitaet", "input_datetime")
