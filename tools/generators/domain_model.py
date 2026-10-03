"""Shared, deterministic loading and presentation of the domain SSOT."""

import json
import os
from pathlib import Path
import shutil
import sys

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from domain_validation import validate_domain


def load_domain(path=None):
    model = yaml.safe_load(Path(path or ROOT / "model/domain.yml").read_text(encoding="utf-8"))
    architecture = yaml.safe_load((ROOT / "model/architecture.yml").read_text(encoding="utf-8"))
    errors = validate_domain(model, architecture)
    if errors:
        raise ValueError("Invalid persistent domain:\n" + "\n".join(errors))
    return model


def write_generated(relative, content):
    target = ROOT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content.rstrip() + "\n", encoding="utf-8")
    print(f"[domain] generated {relative}")


def quote(value):
    return json.dumps(str(value), ensure_ascii=False)


def sql_type(model, entity, attribute):
    if attribute.get("enum"):
        return f"{entity['schema']}.{attribute['enum']}"
    return attribute["type"]


def enum_definitions(model):
    """Copy reused enum concepts into each schema; no cross-schema type dependency."""
    enums = {e["id"]: e for e in model["enums"]}
    result = {}
    for enum in model["enums"]:
        result[(enum["schema"], enum["id"])] = enum["values"]
    for entity in model["entities"]:
        for attribute in entity["attributes"]:
            if attribute.get("enum"):
                result[(entity["schema"], attribute["enum"])] = enums[attribute["enum"]]["values"]
    return sorted(result.items())


def column_note(entity, attribute):
    bits = [attribute["description_es"]]
    if attribute.get("logical_ref"):
        bits.append(f"Referencia lógica a {attribute['logical_ref']}; sin FK física ni navegación ORM cross-context.")
    if attribute.get("assumption"):
        bits.append(f"Assumption: {attribute['assumption']}.")
    bits.append("Fuente: " + ", ".join(attribute.get("source", entity["source"])))
    return " ".join(bits)


def find_tool(name):
    configured = os.environ.get(name.upper().replace('-', '_'))
    if configured:
        found = shutil.which(configured)
        if not found:
            raise RuntimeError(f"Configured tool not found: {configured}")
        return Path(found)
    found = shutil.which(name)
    if found:
        return Path(found)
    # NVM installs already present on this workstation may be outside PATH.
    candidates = sorted(Path.home().glob(f".nvm/versions/node/*/bin/{name}"))
    if len(candidates) == 1:
        return candidates[0]
    raise RuntimeError(f"{name} not found/unambiguous; expose the installed tool in PATH. No packages installed.")


def main_guard(function):
    try:
        function()
    except (ValueError, OSError, RuntimeError, yaml.YAMLError) as exc:
        print(f"[domain] ERROR: {exc}", file=sys.stderr)
        return 1
    return 0
