#!/usr/bin/env python3
"""Compile physical presentation views with canonical runtime facts and icons."""

from __future__ import annotations

import argparse
from html import escape
from pathlib import Path
import subprocess

try:
    from . import logical_presentation as common
    from .icon_map import icon_for, fallback_icon_for
    from .physical import embed_icons
except ImportError:
    import logical_presentation as common
    from icon_map import icon_for, fallback_icon_for
    from physical import embed_icons

ROOT = common.ROOT
MODEL = ROOT / "model/physical_presentation.yml"


def technology_lines(element):
    """Read only declared runtime/technology facts; never infer managed hosts."""
    host = (element.get("host") or {}).get("concrete_service")
    tech = element.get("technology") or {}
    platform = host or tech.get("name") or element.get("provider")
    if element.get("parent_technology") and platform:
        platform = element["parent_technology"] + " / " + platform
    lines = []
    if platform and platform != element["name"]:
        lines.append(platform)
    for section in ("backend", "frontend"):
        stack = element.get(section) or {}
        if stack:
            lines.append(" / ".join(stack[key] for key in ("language", "framework") if stack.get(key)))
    if tech.get("architecture_style"):
        lines.append(tech["architecture_style"])
    if tech.get("application_telemetry"):
        lines.append(tech["application_telemetry"])
    parser = element.get("parser") or {}
    if parser.get("decision_status") == "closed" and parser.get("selected"):
        lines.append(parser["selected"])
    if element.get("model_family"):
        lines.append("Familia " + element["model_family"])
    return [line for line in lines if line]


def node_attributes(element, fallback_icons):
    icon = icon_for(element)
    if icon is None:
        fallback_icons.add(element["id"])
        icon = fallback_icon_for(element)
    # icon_map verifies installed Node subclasses; no diagram instance is needed.
    icon_path = Path(icon._load_icon(icon))
    if not icon_path.is_file():
        raise ValueError(f"Missing installed icon for {element['id']}: {icon_path}")
    name = escape(common.wrapped(element["name"], 24)).replace("\n", "<BR/>")
    details = "<BR/>".join(escape(common.wrapped(line, 27)).replace("\n", "<BR/>")
                           for line in technology_lines(element))
    rows = f'<TR><TD><FONT POINT-SIZE="14">{name}</FONT></TD></TR>'
    if details:
        rows += f'<TR><TD><FONT POINT-SIZE="10" COLOR="#475569">{details}</FONT></TD></TR>'
    label = ('<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="5"><TR>'
             f'<TD WIDTH="44" HEIGHT="44" FIXEDSIZE="TRUE"><IMG SRC="{escape(str(icon_path), quote=True)}" SCALE="TRUE"/></TD>'
             f'<TD><TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2">{rows}</TABLE></TD>'
             '</TR></TABLE>>')
    return {"label": label}


def prepare(presentation, architecture):
    return common.prepare(presentation, architecture, expected_kind="physical_presentation")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    presentation, architecture = common.load_models(MODEL)
    elements, projections = prepare(presentation, architecture)
    fallback_icons = set()
    attributes = {eid: node_attributes(elements[eid], fallback_icons)
                  for eid in sorted({eid for view, _ in projections for eid in view["elements"]})}
    print("fallback_icons: " + str(sorted(fallback_icons)))
    if args.validate_only:
        print("PHYSICAL PRESENTATION VALIDATION PASSED")
        return
    guide = ["# Arquitectura física para sustentación", "",
             "Generado desde `model/physical_presentation.yml`; hechos de `model/architecture.yml`.", "",
             "Diseño propuesto; las figuras no acreditan implementación o despliegue actual.",
             "Los iconos proceden del paquete diagrams instalado; los SVG los incluyen embebidos.",
             "Las agrupaciones son columnas de lectura, no subredes ni nuevos recursos Azure.",
             "Cada nodo declara su propia tecnología. Los componentes internos del diagnóstico se agrupan explícitamente en su contenedor.",
             "PostgreSQL/pgvector representan roles de una sola instancia física (ADR-018); no se confirma un producto Azure para PostgreSQL.",
             "Los protocolos están en los tooltips SVG y en la tabla inferior. Las respuestas síncronas regresan por la misma llamada.", ""]
    covered = set()
    for view, relations in projections:
        source = ROOT / "build" / f"{view['id']}.dot"
        target = ROOT / "out" / f"{view['id']}.svg"
        source.parent.mkdir(exist_ok=True)
        target.parent.mkdir(exist_ok=True)
        source.write_text(common.generate_dot(presentation, elements, view, relations,
                          node_attributes=attributes, model_source="model/physical_presentation.yml"), encoding="utf-8")
        subprocess.run(["dot", "-Tsvg", str(source), "-o", str(target)], check=True, cwd=ROOT)
        embed_icons(target)
        subprocess.run(["dot", "-Tpng", "-Gdpi=160", str(source), "-o", str(target.with_suffix(".png"))], check=True, cwd=ROOT)
        print(f"generated: {target.relative_to(ROOT)} ({len(view['elements'])} nodes)")
        guide.extend([f"## {view['title']}", "", f"[SVG]({view['id']}.svg) · [PNG para diapositivas]({view['id']}.png)", "",
                      f"{len(view['elements'])} nodos. {view['narration'].strip()}", "", view["continuation"], "",
                      "| Relación canónica | Protocolo |", "|---|---|"])
        for r in relations:
            guide.append(f"| {r['label']} | {r['protocol']} |")
            covered.add(r["id"])
        guide.append("")
    guide.extend(["## Relaciones entre vistas", ""])
    collapse = presentation.get("collapse", {})
    for r in architecture["relationships"]:
        if ("derived_from" not in r and r["id"] not in covered
                and collapse.get(r["from"], r["from"]) != collapse.get(r["to"], r["to"])):
            guide.append(f"- `{r['id']}`: {elements[r['from']]['name']} → {elements[r['to']]['name']}: {r['label']} ({r['protocol']}).")
    guide.extend(["", "## Advertencias", "", "Iconos de fallback: " + str(sorted(fallback_icons)), "",
                  "Modelo concreto GPT-4 y modelo de embeddings sin fijar en el SSOT. No se introduce una selección.", ""])
    (ROOT / "out/fisica_expo_guia.md").write_text("\n".join(guide), encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except (KeyError, TypeError, ValueError, OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"Physical presentation failed: {error}") from error
