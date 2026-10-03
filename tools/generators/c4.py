#!/usr/bin/env python3
"""Deterministic C4 projections of model/architecture.yml."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

import yaml


ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "model" / "architecture.yml"
BUILD = ROOT / "build"
OUT = ROOT / "out"
JAR = ROOT / "tools" / "plantuml.jar"
LIBRARIES = {
    "c4_context": "C4_Context",
    "c4_container": "C4_Container",
    "c4_component": "C4_Component",
}
EXTERNAL_KINDS = {"actor", "external_system"}
SAFE_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
STYLES = {"sync": "", "async": "DashedLine()",
          "event": "DottedLine()", "governance": "DashedLine()"}


def text(value):
    """Never stringify missing values or unresolved placeholders."""
    if not isinstance(value, str):
        return ""
    value = " ".join(value.split())
    return "" if value.casefold() in {"none", "null", "tbd"} else value


def quoted(value):
    """Escape model text without enabling PlantUML macro interpolation."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def description(element, layers, warnings):
    candidates = [element.get("description"), element.get("responsibility")]
    for field in ("responsibilities", "capabilities"):
        entries = element.get(field) or []
        candidates.append(entries[0] if entries else None)
    candidates.append((layers.get(element.get("layer")) or {}).get("purpose"))
    for candidate in candidates:
        if value := text(candidate):
            # Only whitespace and truncation change; no translation or invention.
            return value if len(value) <= 90 else value[:89].rstrip() + "…"
    warnings.add(f"{element['id']}: no description basis; using empty string")
    return ""


def technology(element, warnings, *, with_pgvector=False):
    """One null-tolerant resolver, using only the element's own model fields."""
    host = element.get("host") or {}
    tech = element.get("technology") or {}
    concrete = text(host.get("concrete_service"))
    named = text(tech.get("name"))
    if with_pgvector:
        # Explicitly authorized shared-PostgreSQL C4 projection.
        return "PostgreSQL / pgvector"
    if concrete:
        framework = text(tech.get("framework"))
        style = text(tech.get("architecture_style"))
        if element["id"] == "web_dashboard" and framework and style:
            return f"{framework} {style} / {concrete}"
        return concrete
    if named:
        parent = text(element.get("parent_technology"))
        return f"{parent} / {named}" if parent else named
    provider = text(element.get("provider"))
    family = text(element.get("model_family"))
    model = text(element.get("model"))
    if provider:
        detail = model or (f"{family} family" if family else "")
        return " / ".join(part for part in (provider, detail) if part)
    framework = text(tech.get("framework"))
    if framework:
        return " ".join(part for part in
                        (framework, text(tech.get("architecture_style"))) if part)
    parser = text((element.get("parser") or {}).get("selected"))
    if parser:
        return parser
    warnings.add(f"{element['id']}: no technology specified; using empty string")
    return ""


@dataclass
class Projection:
    view: dict
    inside: list[dict]
    outside: list[dict]
    relationships: list[dict]
    combined_postgres: bool = False

    @property
    def count(self):
        return len(self.inside) + len(self.outside)


def project(model, view, elements, warnings):
    kind = view["kind"]
    relationships = model["relationships"]
    if kind == "c4_context":
        def endpoint(eid):
            return eid if elements[eid]["kind"] in EXTERNAL_KINDS else "aiops"

        # Canonical YAML order defines the first two unique labels.
        grouped = {}
        for rel in relationships:
            if "derived_from" in rel:
                continue
            src, dst = endpoint(rel["from"]), endpoint(rel["to"])
            if src == dst:
                continue
            group = grouped.setdefault((src, dst), {
                "from": src, "to": dst, "ids": [], "labels": [],
                "protocols": [], "styles": [],
            })
            group["ids"].append(rel["id"])
            for field, plural in (("label", "labels"), ("protocol", "protocols"),
                                  ("style", "styles")):
                if rel[field] not in group[plural]:
                    group[plural].append(rel[field])
        selected = []
        for group in grouped.values():
            if len(group["styles"]) > 1:
                warnings.add(
                    f"{view['id']}: aggregated {group['from']} -> {group['to']} "
                    f"retains multiple style tags: {'+'.join(group['styles'])}"
                )
            selected.append({
                "id": ", ".join(group["ids"]),
                "from": group["from"], "to": group["to"],
                "label": " / ".join(group["labels"][:2]),
                "protocol": " / ".join(group["protocols"]),
                "style": "+".join(group["styles"]),
            })
        connected = {r[end] for r in selected for end in ("from", "to")}
        outside = [e for e in model["elements"]
                   if e["id"] in connected and e["kind"] in EXTERNAL_KINDS]
        central = {**model["architecture"], "id": "aiops", "kind": "software_system"}
        return Projection(view, [central], outside, selected)

    members = view["elements"]
    chosen = [elements[eid] for eid in members]
    combined = (kind == "c4_container" and
                {"postgresql_operational_store", "pgvector_knowledge_store"}
                <= set(members))

    def endpoint(eid):
        elem = elements[eid]
        if kind == "c4_container" and elem["kind"] == "component":
            eid = elem["parent"]
        if combined and eid == "pgvector_knowledge_store":
            eid = "postgresql_operational_store"
        return eid

    if combined:
        chosen = [e for e in chosen if e["id"] != "pgvector_knowledge_store"]
    included = {e["id"] for e in chosen}
    if kind == "c4_container":
        inside = [e for e in chosen if e["kind"] in {"container", "datastore"}]
        outside = [e for e in chosen if e["kind"] in EXTERNAL_KINDS]
        if len(inside) + len(outside) != len(chosen):
            raise ValueError(f"{view['id']}: Level 2 membership must use container-level IDs")
        candidates = [r for r in relationships if "derived_from" not in r]
    else:
        target = view["container"]
        inside = [e for e in chosen if e["kind"] == "component"]
        if any(e.get("parent") != target for e in inside):
            raise ValueError(f"{view['id']}: component parent differs from boundary")
        outside = [e for e in chosen if e["kind"] != "component"]
        component_ids = {e["id"] for e in inside}
        derived = [r for r in relationships if "derived_from" in r
                   and r["from"] in included and r["to"] in included]
        replaced = {r["derived_from"] for r in derived}
        # Only component edges belong in this zoom; keep governance persistence.
        candidates = derived + [r for r in relationships
                                if "derived_from" not in r
                                and r["id"] not in replaced
                                and (r["from"] in component_ids
                                     or r["to"] in component_ids)]
    # The declared membership already describes each flow. Do not add optional
    # undeclared neighbours or recursively expand the graph.
    selected, seen = [], set()
    for rel in candidates:
        src, dst = endpoint(rel["from"]), endpoint(rel["to"])
        if src not in included or dst not in included or src == dst:
            continue
        key = (src, dst, rel["label"], rel["protocol"], rel["style"])
        if key not in seen:
            seen.add(key)
            selected.append({**rel, "from": src, "to": dst})
    return Projection(view, inside, outside, selected, combined)


def prepare(model):
    elements = {e["id"]: e for e in model["elements"]}
    views = {v["id"]: v for v in model["views"]}
    limit = model["architecture"]["view_constraints"]["max_nodes_per_view"]
    if type(limit) is not int or limit < 1:
        raise ValueError("max_nodes_per_view must be a positive integer")
    warnings = set()
    for rel in model["relationships"]:
        if rel.get("from") not in elements or rel.get("to") not in elements:
            raise ValueError(f"{rel['id']}: unknown relationship endpoint")
        for field in ("label", "protocol"):
            if not text(rel.get(field)):
                raise ValueError(f"{rel['id']}: missing or unresolved {field}")
        if rel.get("style") not in STYLES:
            raise ValueError(f"{rel['id']}: unsupported style")
        if "derived_from" in rel and rel["derived_from"] not in {
                r["id"] for r in model["relationships"]}:
            raise ValueError(f"{rel['id']}: unknown derived_from relationship")
    projections = []
    for view in model["views"]:
        kind = view["kind"]
        if kind not in LIBRARIES:
            continue
        vid = view["id"]
        if not SAFE_ID.fullmatch(vid) or not text(view.get("title")):
            raise ValueError(f"{vid}: invalid ID or missing title")
        if len(set(view.get("elements", []))) != len(view.get("elements", [])):
            raise ValueError(f"{vid}: duplicate membership")
        for eid in view.get("elements", []):
            if eid not in elements:
                raise ValueError(f"{vid}: unknown view element {eid}")
        if "zoom_from" in view and view["zoom_from"] not in views:
            raise ValueError(f"{vid}: unknown zoom_from view")
        if kind == "c4_component":
            target = view.get("container")
            if (target not in elements or elements[target]["kind"] != "container"
                    or target != view.get("zoom_target")):
                raise ValueError(f"{vid}: invalid container/zoom_target")
        elif view.get("zoom_target") != model["architecture"]["id"]:
            raise ValueError(f"{vid}: zoom_target differs from software system")
        projection = project(model, view, elements, warnings)
        if not view.get("include_external", True) and projection.outside:
            raise ValueError(f"{vid}: external members conflict with include_external=false")
        if projection.count > limit:
            raise ValueError(f"{vid}: {projection.count} nodes including stubs exceeds {limit}")
        aliases = {e["id"] for e in projection.inside + projection.outside}
        boundary = view.get("container", "aiops")
        if kind != "c4_context" and boundary in aliases:
            raise ValueError(f"{vid}: boundary alias collides with a node")
        for alias in aliases | {boundary}:
            if not SAFE_ID.fullmatch(alias):
                raise ValueError(f"{vid}: unsafe alias {alias!r}")
        final = view.get("final") is True or view.get("status") == "final"
        if final:
            for elem in projection.inside + projection.outside:
                if elem.get("status") == "open_question":
                    raise ValueError(f"{vid}: final view contains open_question {elem['id']}")
        projections.append(projection)
    return projections, warnings


def node_line(element, macro, layers, warnings, combined=False):
    alias, name = element["id"], text(element.get("name"))
    if not name:
        raise ValueError(f"{alias}: missing node name")
    desc = description(element, layers, warnings)
    if macro in {"Person", "System"}:
        return f"{macro}({alias}, {quoted(name)}, {quoted(desc)})"
    tech = technology(element, warnings, with_pgvector=combined)
    if macro == "System_Ext":
        return f"{macro}({alias}, {quoted(name)}, {quoted(desc)}, $type={quoted(tech)})"
    return f"{macro}({alias}, {quoted(name)}, {quoted(tech)}, {quoted(desc)})"


def generate_puml(model, projection, warnings):
    view = projection.view
    kind = view["kind"]
    layers = {layer["id"]: layer for layer in model["layers"]}
    lines = [
        "@startuml",
        "' Generated from model/architecture.yml; do not edit manually.",
        f"' Architectural nodes including stubs: {projection.count}",
        f"!include <C4/{LIBRARIES[kind]}>",
        "LAYOUT_TOP_DOWN()",
        "LAYOUT_WITH_LEGEND()",
        "skinparam defaultFontName DejaVu Sans",
        "skinparam nodesep 35",
        "skinparam ranksep 45",
        f"title {text(view['title'])}",
    ]
    for style, line_style in STYLES.items():
        parameter = f", $lineStyle={line_style}" if line_style else ""
        lines.append(f"AddRelTag({quoted(style)}{parameter}, $legendText={quoted(style)})")
    lines.append("")
    for element in projection.outside:
        macro = {"actor": "Person", "external_system": "System_Ext",
                 "container": "Container_Ext", "datastore": "ContainerDb_Ext"}[element["kind"]]
        lines.append(node_line(element, macro, layers, warnings))
    if kind == "c4_context":
        lines.append(node_line(projection.inside[0], "System", layers, warnings))
    else:
        if kind == "c4_container":
            lines.append(f"System_Boundary(aiops, {quoted(model['architecture']['name'])}) {{")
        else:
            target = view["container"]
            container = next(e for e in model["elements"] if e["id"] == target)
            lines.append(f"Container_Boundary({target}, {quoted(container['name'])}) {{")
        for element in projection.inside:
            macro = {"container": "Container", "datastore": "ContainerDb",
                     "component": "Component"}[element["kind"]]
            combined = (projection.combined_postgres
                        and element["id"] == "postgresql_operational_store")
            lines.append("  " + node_line(element, macro, layers, warnings, combined))
        lines.append("}")
    lines.append("")
    for rel in projection.relationships:
        lines.append(f"' {rel['id']}")
        lines.append(
            f"Rel({rel['from']}, {rel['to']}, {quoted(rel['label'])}, "
            f"{quoted(rel['protocol'])}, $tags={quoted(rel['style'])})"
        )
    lines.extend(["", "SHOW_LEGEND()", "@enduml", ""])
    return "\n".join(lines)


def compile_svg(paths):
    # An absolute output directory prevents PlantUML's input-relative defaults.
    command = ["java", "-jar", str(JAR), "-charset", "UTF-8", "-tsvg",
               "-failfast2", "-nometadata", "-o", str(OUT), *map(str, paths)]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        if result.stdout:
            print(result.stdout, file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode
    for path in paths:
        svg = OUT / f"{path.stem}.svg"
        if not svg.is_file() or svg.stat().st_size == 0:
            raise ValueError(f"PlantUML did not produce a nonempty {svg}")
        if ET.parse(svg).getroot().tag != "{http://www.w3.org/2000/svg}svg":
            raise ValueError(f"PlantUML output is not SVG: {svg}")
    return 0


def main():
    warnings = set()
    try:
        with MODEL.open(encoding="utf-8") as stream:
            model = yaml.safe_load(stream)
        projections, warnings = prepare(model)
        # Complete preflight before writing any generated files.
        sources = [(p, generate_puml(model, p, warnings)) for p in projections]
        BUILD.mkdir(parents=True, exist_ok=True)
        OUT.mkdir(parents=True, exist_ok=True)
        paths = []
        for projection, source in sources:
            path = BUILD / f"{projection.view['id']}.puml"
            path.write_text(source, encoding="utf-8")
            paths.append(path)
        code = compile_svg(paths)
        if code:
            return code
        for projection, _ in sources:
            vid = projection.view["id"]
            print(f"generated: build/{vid}.puml -> out/{vid}.svg; "
                  f"nodes={projection.count} "
                  f"(inside={len(projection.inside)}, outside/stubs={len(projection.outside)})")
    except (KeyError, TypeError, ValueError, OSError, ET.ParseError) as error:
        print(f"C4 generation failed: {error}", file=sys.stderr)
        return 1
    finally:
        for warning in sorted(warnings):
            print(f"WARNING: {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
