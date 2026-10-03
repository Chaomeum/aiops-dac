#!/usr/bin/env python3
"""Compile the class-design SSOT into exactly three PlantUML/SVG figures."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from validate_design import load_models, validate_design  # noqa: E402

BUILD = ROOT / "build"
OUT = ROOT / "out"
JAR = ROOT / "tools/plantuml.jar"
LAYERS = ("interfaces", "application", "domain", "infrastructure", "external")
COLORS = {"interfaces": "#EAF2FA", "application": "#EDF5F0",
          "domain": "#FFF7E8", "infrastructure": "#F1EFF7",
          "external": "#F0F0F0"}


def literal(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("empty/non-string diagram text")
    if re.search(r"\b(?:None|null|TBD)\b", value):
        raise ValueError(f"unresolved diagram text: {value!r}")
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def node_lines(item):
    kind = item.get("kind", "class")
    cid = item["id"]
    lines = [f'{kind} "{literal(item["name"])}" as {cid} <<{item["stereotype"]}>> {{']
    for value in item.get("values", []):
        lines.append(f"  {literal(value)}")
    for attribute in item["attributes"]:
        optional = " [optional]" if attribute.get("nullable") else ""
        lines.append(f'  -{attribute["name"]}: {literal(attribute["type"])}{optional}')
    for method in item["methods"]:
        # Parameter types retain the contract, while names are available in SSOT.
        params = ", ".join(literal(p["type"]) for p in method["parameters"])
        lines.append(f'  +{method["name"]}({params}): {literal(method["returns"])}')
    lines.append("}")
    annotations = []
    if item.get("persisted_as"):
        annotations.append("persisted_as: " + item["persisted_as"])
    if item.get("persistence"):
        annotations.extend(["PostgreSQL común:", *item["persistence"]["tables"]])
    annotations.extend(item.get("notes", []))
    if annotations:
        lines.extend([f"note bottom of {cid}",
                      *["  " + literal(note) for note in annotations], "end note"])
    return lines


def generate_puml(design, diagram):
    classes = {item["id"]: item for item in design["classes"]}
    members = diagram["elements"]
    groups = defaultdict(lambda: defaultdict(list))
    for cid in members:
        item = classes[cid]
        groups[item["layer"]][item["package"]].append(item)
    lines = [
        "@startuml",
        "' Generated from model/design.yml; do not edit manually.",
        f"' Class/proxy nodes: {len(members)}",
        "top to bottom direction",
        "hide empty members",
        "hide circle",
        "skinparam classAttributeIconSize 0",
        "skinparam defaultFontName DejaVu Sans",
        "skinparam defaultFontSize 12",
        "skinparam shadowing false",
        "skinparam packageStyle rectangle",
        "skinparam nodesep 40",
        "skinparam ranksep 55",
        "skinparam ArrowColor #536578",
        "skinparam classBorderColor #536578",
        "skinparam NoteBackgroundColor #FFFFF4",
        "skinparam NoteBorderColor #C9BB8B",
        "title",
        literal(diagram["title"]),
        f'Zoom-In: {literal(diagram["zoom_target"])}',
        "end title",
        f'footer Modelo {literal(design["model_version"])} - {diagram["id"]} - Diseño propuesto',
        "",
    ]
    for index, layer in enumerate(LAYERS):
        if layer not in groups:
            continue
        label = layer + "\\n" + "\\n".join(groups[layer])
        lines.append(f'package "{label}" as layer_{index} {COLORS[layer]} {{')
        for items in groups[layer].values():
            for item in items:
                lines.extend("  " + line for line in node_lines(item))
        lines.extend(["}", ""])
    # Presentation-only anchors order layer clusters vertically. They add no
    # classes or dependency semantics to the model or membership lists.
    anchors = [next(iter(groups[layer].values()))[0]["id"]
               for layer in LAYERS if layer in groups]
    for before, after in zip(anchors, anchors[1:]):
        lines.append(f"{before} -[hidden]down-> {after}")
    for rel in design["relationships"]:
        if rel["from"] not in members or rel["to"] not in members:
            continue
        arrow = "..|>" if rel["type"] == "implements" else "-->"
        src_layer = LAYERS.index(classes[rel["from"]]["layer"])
        dst_layer = LAYERS.index(classes[rel["to"]]["layer"])
        if src_layer != dst_layer:
            direction = "down" if src_layer < dst_layer else "up"
            arrow = f"..{direction}|>" if rel["type"] == "implements" else f"-{direction}->"
        if rel.get("ownership") == "composition":
            arrow = "*--"
        multiplicity = f' "{literal(rel["multiplicity"])}"' if rel.get("multiplicity") else ""
        label = rel.get("label", rel["type"])
        if rel.get("protocol"):
            label += " / " + rel["protocol"]
        lines.append(f'{rel["from"]} {arrow}{multiplicity} {rel["to"]} : {literal(label)}')
    lines.extend(["", "legend bottom"])
    lines.append("  recommendation_service / Java / Spring Boot / status: proposed")
    lines.append("  CQRS lógico / misma instancia PostgreSQL / dependencias por interfaces")
    for note in diagram.get("notes", []):
        lines.append("  " + literal(note))
    lines.extend(["endlegend", "@enduml", ""])
    return "\n".join(lines)


def navigation_markdown(design, architecture):
    """Link existing C4 figures without regenerating or changing C4 sources."""
    views = {item["id"]: item for item in architecture["views"]}
    nav = design["design_rules"]["navigation_views"]
    lines = ["# Navegación C4 → diseño de clases", "",
             f"Modelo {design['model_version']} — Diseño propuesto", "",
             "SSOT: `model/design.yml`. Las figuras C4 existentes conservan su modelo y membresía.", ""]
    for diagram in design["class_diagrams"]:
        did, zoom = diagram["id"], diagram["zoom_target"]
        lines.extend([
            f"## {diagram['title']}", "",
            " → ".join([
                f"[C4 Context (`{nav[0]}`)]({nav[0]}.svg)",
                *[f"[`{vid}`]({vid}.svg)" for vid in nav[1:]],
                f"`{zoom}`", f"[{did}]({did}.svg)",
            ]), "",
            f"Zoom-In: `{zoom}`; {len(diagram['elements'])} clases/nodos, incluidos proxies.", "",
        ])
    lines.extend([
        "`diagnostic_output_component` se realiza dentro de CD-2 por `DiagnosticOutputComposer` y su dominio interno.", "",
        f"La vista `{nav[-1]}` amplía `{views[nav[-1]]['zoom_target']}` desde `{views[nav[-1]]['zoom_from']}`.", "",
        "Las clases compartidas de CD-1 son referencias al mismo diseño detallado en CD-2/CD-3; se cuentan en cada figura.", "",
    ])
    return "\n".join(lines)


def compile_svgs(paths):
    command = ["java", "-Djava.awt.headless=true", "-jar", str(JAR), "-charset", "UTF-8",
               "-tsvg", "-failfast2", "-nometadata", "-o", str(OUT), *map(str, paths)]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        raise ValueError(f"PlantUML failed ({result.returncode}): {result.stdout}\n{result.stderr}")
    for source in paths:
        svg = OUT / f"{source.stem}.svg"
        if not svg.is_file() or not svg.stat().st_size:
            raise ValueError(f"missing/empty SVG: {svg}")
        tree = ET.parse(svg)
        if tree.getroot().tag != "{http://www.w3.org/2000/svg}svg":
            raise ValueError(f"not an SVG: {svg}")
        visible = " ".join("".join(node.itertext()) for node in tree.iter("{http://www.w3.org/2000/svg}text"))
        if re.search(r"\b(?:None|null|TBD)\b", visible):
            raise ValueError(f"unresolved visible placeholder in {svg}")


def main():
    defaults = [ROOT / "model/design.yml", ROOT / "model/architecture.yml", ROOT / "model/domain.yml"]
    paths = [Path(sys.argv[i + 1]) if len(sys.argv) > i + 1 else path for i, path in enumerate(defaults)]
    try:
        design, architecture, domain = load_models(paths)
        errors = validate_design(design, architecture, domain)
        if errors:
            raise ValueError("design preflight failed:\n" + "\n".join(errors))
        # Complete all model/text preflight before touching generated files.
        sources = [(diagram, generate_puml(design, diagram)) for diagram in design["class_diagrams"]]
        navigation = navigation_markdown(design, architecture)
        BUILD.mkdir(parents=True, exist_ok=True)
        OUT.mkdir(parents=True, exist_ok=True)
        generated = []
        for diagram, source in sources:
            path = BUILD / f"{diagram['id']}.puml"
            path.write_text(source, encoding="utf-8")
            generated.append(path)
        compile_svgs(generated)
        (OUT / "navegacion_zoom.md").write_text(navigation, encoding="utf-8")
        for diagram, _ in sources:
            print(f"generated: build/{diagram['id']}.puml -> out/{diagram['id']}.svg; "
                  f"nodes={len(diagram['elements'])}")
        print("generated: out/navegacion_zoom.md")
    except Exception as exc:
        print(f"Class generation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
