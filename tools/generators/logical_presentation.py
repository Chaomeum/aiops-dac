#!/usr/bin/env python3
"""Render explicitly declared presentation views, referencing canonical facts."""

from __future__ import annotations

import argparse
from html import escape
from pathlib import Path
import re
import subprocess
import textwrap

import yaml
from graphviz import Digraph

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "model/logical_presentation.yml"
SAFE_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def load_models():
    presentation = yaml.safe_load(MODEL.read_text(encoding="utf-8"))
    source = ROOT / presentation["architecture_source"]
    if source.resolve() != (ROOT / "model/architecture.yml").resolve():
        raise ValueError("architecture_source must reference model/architecture.yml")
    return presentation, yaml.safe_load(source.read_text(encoding="utf-8"))


def prepare(presentation, architecture):
    elements = {e["id"]: e for e in architecture["elements"]}
    relations = {r["id"]: r for r in architecture["relationships"]}
    collapse = presentation.get("collapse", {})
    for child, parent in collapse.items():
        if (child not in elements or parent not in elements
                or elements[child].get("kind") != "component"
                or elements[child].get("parent") != parent
                or elements[parent]["kind"] != "container"):
            raise ValueError(f"Invalid explicit component collapse: {child} -> {parent}")
    labels = presentation["relationship_labels"]
    if labels.keys() - relations.keys():
        raise ValueError("Presentation labels reference unknown relationships")
    limit = architecture["architecture"]["view_constraints"]["max_nodes_per_view"]
    projections = []
    seen = set()
    covered = set()
    for view in presentation["views"]:
        vid = view["id"]
        if not SAFE_ID.fullmatch(vid) or vid in seen:
            raise ValueError(f"Invalid/duplicate view ID: {vid}")
        seen.add(vid)
        if view["kind"] != "logical_presentation" or not view.get("title"):
            raise ValueError(f"{vid}: missing title or invalid kind")
        members = view["elements"]
        if len(set(members)) != len(members) or not 1 <= len(members) <= limit:
            raise ValueError(f"{vid}: duplicate membership or node limit exceeded")
        if type(view.get("include_external")) is not bool:
            raise ValueError(f"{vid}: include_external must be boolean")
        groups = view["groups"]
        group_ids = [g["id"] for g in groups]
        grouped = [eid for g in groups for eid in g["elements"]]
        if (len(set(group_ids)) != len(group_ids)
                or any(not SAFE_ID.fullmatch(gid) for gid in group_ids)
                or len(grouped) != len(set(grouped)) or set(grouped) != set(members)):
            raise ValueError(f"{vid}: visual groups must partition declared membership")
        for eid in members:
            if eid not in elements or eid in collapse:
                raise ValueError(f"{vid}: unknown or explicitly collapsed member {eid}")
            e = elements[eid]
            if not view["include_external"] and e["kind"] == "external_system":
                raise ValueError(f"{vid}: external member with include_external=false")
            if (view.get("final") or view.get("status") == "final") and e["status"] == "open_question":
                raise ValueError(f"{vid}: final view includes open_question {eid}")
        selected = []
        for r in relations.values():
            # Internal C4 projections must not duplicate canonical container edges.
            if "derived_from" in r:
                continue
            src, dst = (collapse.get(r[end], r[end]) for end in ("from", "to"))
            if src == dst or src not in members or dst not in members:
                continue
            if r["id"] not in labels or not labels[r["id"]]:
                raise ValueError(f"{vid}: missing presentation label for {r['id']}")
            selected.append({**r, "from": src, "to": dst})
        connected = {r[end] for r in selected for end in ("from", "to")}
        if set(members) - connected:
            raise ValueError(f"{vid}: isolated members: {sorted(set(members) - connected)}")
        projections.append((view, selected))
        covered.update(members)
    if missing := set(elements) - covered - set(collapse):
        raise ValueError(f"Canonical elements missing from presentation: {sorted(missing)}")
    return elements, projections


def wrapped(value, width=26):
    return "\n".join(textwrap.wrap(value, width, break_long_words=False, break_on_hyphens=False))


def generate_dot(presentation, elements, view, relations):
    graph = Digraph(view["id"], comment="GENERATED — sources: model/logical_presentation.yml + model/architecture.yml")
    heading = ('<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="3">'
               f'<TR><TD><FONT POINT-SIZE="22">{escape(view["title"])}</FONT></TD></TR>'
               '<TR><TD><FONT POINT-SIZE="11">Diseño propuesto · Azul: prototipo · Gris: actores y sistemas externos · Verde: persistencia</FONT></TD></TR>'
               '<TR><TD><FONT POINT-SIZE="11">Continua: síncrona · Discontinua: asíncrona · Punteada: evento · Protocolos en tooltip y guía</FONT></TD></TR>'
               f'<TR><TD><FONT POINT-SIZE="12">{escape(wrapped(view["continuation"], 95)).replace(chr(10), "<BR/>")}</FONT></TD></TR>'
               '</TABLE>>')
    graph.attr(rankdir="LR", bgcolor="white", pad="0.25", nodesep="0.45", ranksep="0.65",
               fontname="DejaVu Sans", fontsize="20", labelloc="t", compound="true",
               label=heading)
    graph.attr("node", shape="box", style="rounded,filled", fontname="DejaVu Sans",
               fontsize="15", margin="0.18,0.12", penwidth="1.5")
    graph.attr("edge", fontname="DejaVu Sans", fontsize="11", color="#475569", arrowsize="0.7")
    groups = {eid: group["id"] for group in view["groups"] for eid in group["elements"]}
    for group in view["groups"]:
        with graph.subgraph(name="cluster_" + group["id"]) as cluster:
            cluster.attr(label=wrapped(group["title"]), fontsize="13", color="#CBD5E1",
                         style="rounded", margin="18", rank="same")
            for eid in group["elements"]:
                e = elements[eid]
                attrs = {"fillcolor": "#EFF6FF", "color": "#2563EB"}
                if e["kind"] in {"actor", "external_system"}:
                    attrs.update(fillcolor="#F1F5F9", color="#64748B", style="dashed,filled")
                if e["kind"] == "actor":
                    attrs.update(shape="oval", style="filled")
                if e["kind"] == "datastore":
                    attrs.update(shape="cylinder", fillcolor="#ECFDF5", color="#059669")
                tooltip = f'{eid} | {e["kind"]} | {e["layer"]} | status: {e["status"]}'
                if eid == "recommendation_service":
                    tooltip += " | Componentes agrupados: " + ", ".join(
                        elements[child]["name"] for child, parent in presentation["collapse"].items() if parent == eid
                    )
                cluster.node(eid, wrapped(e["name"]), tooltip=tooltip, **attrs)
    for r in relations:
        label = wrapped(presentation["relationship_labels"][r["id"]], 24)
        if presentation.get("show_protocols", True):
            label += "\n(" + r["protocol"] + ")"
        within_group = groups[r["from"]] == groups[r["to"]]
        edge_label = {"xlabel": label} if within_group else {"label": label}
        graph.edge(r["from"], r["to"], id=r["id"], **edge_label,
                   tooltip=r["label"] + " (" + r["protocol"] + ")",
                   constraint="false" if within_group else "true",
                   style={"sync": "solid", "async": "dashed", "event": "dotted", "governance": "dashed"}[r["style"]])
    return graph.source


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    presentation, architecture = load_models()
    elements, projections = prepare(presentation, architecture)
    if args.validate_only:
        print("LOGICAL PRESENTATION VALIDATION PASSED")
        return
    guide = ["# Arquitectura lógica para sustentación", "",
             "Generado desde `model/logical_presentation.yml`, con hechos de `model/architecture.yml`.", "",
             "Diseño propuesto; estas figuras no acreditan implementación. Lectura de izquierda a derecha.", "",
             "Los componentes internos del servicio diagnóstico se agrupan explícitamente en su contenedor.",
             "Se omiten conexiones que salen de cada vista; las notas indican su continuación.",
             "PostgreSQL y pgvector son roles lógicos de una misma instancia física según ADR-018.", ""]
    for view, relations in projections:
        source = ROOT / "build" / f"{view['id']}.dot"
        target = ROOT / "out" / f"{view['id']}.svg"
        source.parent.mkdir(exist_ok=True)
        target.parent.mkdir(exist_ok=True)
        source.write_text(generate_dot(presentation, elements, view, relations), encoding="utf-8")
        subprocess.run(["dot", "-Tsvg", str(source), "-o", str(target)], check=True, cwd=ROOT)
        subprocess.run(["dot", "-Tpng", "-Gdpi=160", str(source), "-o", str(target.with_suffix(".png"))], check=True, cwd=ROOT)
        print(f"generated: {target.relative_to(ROOT)} ({len(view['elements'])} nodes)")
        guide.extend([f"## {view['title']}", "", f"[Abrir SVG]({view['id']}.svg) · [PNG para diapositivas]({view['id']}.png)", "",
                      f"{len(view['elements'])} nodos. {view['narration'].strip()}", "",
                      view["continuation"], ""])
    guide.extend(["## Relaciones representadas y protocolos", "",
                  "Las cajas de agrupación organizan la lectura; no son nuevos elementos arquitectónicos.", "",
                  "| Relación canónica | Protocolo | Vistas |", "|---|---|---|"])
    for r in architecture["relationships"]:
        in_views = [v["id"] for v, relations in projections if any(edge["id"] == r["id"] for edge in relations)]
        if in_views:
            guide.append(f"| {r['label']} | {r['protocol']} | {', '.join(in_views)} |")
    guide.append("")
    covered = {r["id"] for _, relations in projections for r in relations}
    omitted = [r for r in architecture["relationships"] if "derived_from" not in r
               and r["id"] not in covered
               and presentation["collapse"].get(r["from"], r["from"]) != presentation["collapse"].get(r["to"], r["to"])]
    if omitted:
        guide.extend(["## Relaciones entre vistas", ""])
        for r in omitted:
            guide.append(f"- `{r['id']}`: {elements[r['from']]['name']} → {elements[r['to']]['name']}: {r['label']} ({r['protocol']}).")
    (ROOT / "out/logica_expo_guia.md").write_text("\n".join(guide) + "\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except (KeyError, TypeError, ValueError, OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"Logical presentation failed: {error}") from error
