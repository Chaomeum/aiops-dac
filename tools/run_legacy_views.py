#!/usr/bin/env python3
"""Run unchanged legacy renderers without the C4-only ADR-017 projections."""

import importlib.util
from pathlib import Path
import sys


def legacy_projection(model):
    # ADR-017 introduces internal components and relations exclusively for the
    # C4 Level 3 zoom. Keep the existing human-review component and its edges.
    c4_components = {
        element["id"] for element in model["elements"]
        if element.get("kind") == "component"
        and "SRC_ADR_017" in (element.get("source") or [])
    }
    return {
        **model,
        "elements": [e for e in model["elements"] if e["id"] not in c4_components],
        "relationships": [
            r for r in model["relationships"]
            if "SRC_ADR_017" not in (r.get("source") or [])
            and r["from"] not in c4_components and r["to"] not in c4_components
        ],
        # The physical renderer expects membership lists for every view it
        # preflights. Context has no list; only physical views belong here.
        "views": [v for v in model["views"] if not v["kind"].startswith("c4_")],
    }


def main():
    path = Path(sys.argv[1]).resolve()
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("legacy_renderer", path)
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)
    if path.stem == "physical":
        prepare = renderer.prepare
        renderer.prepare = lambda model: prepare(legacy_projection(model))
    elif path.stem == "logical":
        load_model = renderer.load_model
        renderer.load_model = lambda: legacy_projection(load_model())
    else:
        raise ValueError(f"Unsupported legacy renderer: {path}")
    return renderer.main()


if __name__ == "__main__":
    sys.exit(main())
