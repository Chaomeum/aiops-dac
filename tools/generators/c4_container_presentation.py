#!/usr/bin/env python3
"""Slide-sized C4 container projections with complete node/relationship coverage."""

from __future__ import annotations

import argparse
from html import escape
from pathlib import Path
import subprocess
import textwrap

from graphviz import Digraph

try:
    from . import c4
    from .logical_presentation import load_models
    from .physical_presentation import technology_lines
except ImportError:
    import c4
    from logical_presentation import load_models
    from physical_presentation import technology_lines

ROOT = c4.ROOT
MODEL = ROOT / "model/c4_container_presentation.yml"
NODE_WIDTH = 238
NODE_HEIGHT = 174


def lines(value, width=28):
    return "<BR/>".join(escape(line) for line in textwrap.wrap(value, width, break_long_words=False, break_on_hyphens=False))


def prepare(presentation, architecture):
    if presentation["architecture_source"] != "model/architecture.yml":
        raise ValueError("Expected canonical architecture_source")
    if presentation.get("projection") != "canonical_c4_container":
        raise ValueError("Expected canonical C4 projection")
    if presentation.get("canvas") != {"width": 1920, "height": 1080}:
        raise ValueError("Expected 1920x1080 canvas")
    if presentation.get("collapse") != {"human_review_component": "recommendation_service", "pgvector_knowledge_store": "postgresql_operational_store"}:
        raise ValueError("Unexpected C4 presentation collapse")
    projections, _ = c4.prepare(architecture)
    canonical = {p.view["id"]: p for p in projections if p.view["kind"] == "c4_container"}
    seen = set()
    result = []
    for view in presentation["views"]:
        if not c4.SAFE_ID.fullmatch(view["id"]) or view["id"] in seen:
            raise ValueError("Invalid/duplicate presentation ID")
        seen.add(view["id"])
        if view["kind"] != "c4_container_presentation" or view["source_view"] not in canonical:
            raise ValueError("Expected an existing C4 container view")
        projection = canonical[view["source_view"]]
        if view["elements"] != projection.view["elements"]:
            raise ValueError(f"{view['id']}: membership must exactly match canonical view")
        if type(view["include_external"]) is not bool or view["include_external"] != projection.view["include_external"]:
            raise ValueError("include_external must match canonical view")
        nodes = projection.inside + projection.outside
        if set(view["positions"]) != {e["id"] for e in nodes}:
            raise ValueError("Positions must cover exactly the projected C4 nodes")
        for e in nodes:
            pos = view["positions"][e["id"]]
            if (not isinstance(pos, list) or len(pos) != 2
                    or any(type(v) not in (int, float) for v in pos)
                    or not 130 <= pos[0] <= 1300 or not 180 <= pos[1] <= 850):
                raise ValueError(f"Invalid node position: {e['id']}")
            if not presentation["node_summaries"].get(e["id"]):
                raise ValueError(f"Missing node summary: {e['id']}")
        for r in projection.relationships:
            if not presentation["relationship_labels"].get(r["id"]):
                raise ValueError(f"Missing relationship label: {r['id']}")
        if set(view["routes"]) != {r["id"] for r in projection.relationships}:
            raise ValueError("Routes must cover every canonical relationship exactly")
        for route in view["routes"].values():
            if route["from"] not in {"n", "e", "w", "s"} or route["to"] not in {"n", "e", "w", "s"}:
                raise ValueError("Invalid route port")
            for field in ("from_offset", "to_offset"):
                if type(route.get(field, 0)) not in (int, float) or abs(route.get(field, 0)) > 60:
                    raise ValueError("Invalid route port offset")
            for point in [route["label"], *route["via"]]:
                if (len(point) != 2 or any(type(v) not in (int, float) for v in point)
                        or not 10 <= point[0] <= 1450 or not 135 <= point[1] <= 915):
                    raise ValueError("Invalid route coordinates")
        for r in projection.relationships:
            points = route_geometry(view, r)
            edge_position(points)
            for eid, center in view["positions"].items():
                if eid in (r["from"], r["to"]):
                    continue
                for a, b in zip(points, points[1:]):
                    if crosses_box(a, b, center):
                        raise ValueError(f"{r['id']}: route crosses node {eid}")
        # The prototype frame is a presentation artifact; ensure it represents
        # exactly the canonical inside/outside classification.
        for node in projection.inside:
            x, y = view["positions"][node["id"]]
            if not (315 + NODE_WIDTH / 2 <= x <= 1445 - NODE_WIDTH / 2
                    and 140 + NODE_HEIGHT / 2 <= y <= 950 - NODE_HEIGHT / 2):
                raise ValueError("Internal node outside prototype frame")
        for node in projection.outside:
            x, _ = view["positions"][node["id"]]
            if x + NODE_WIDTH / 2 >= 315:
                raise ValueError("External node inside prototype frame")
        result.append((view, projection))
    if sorted(v["source_view"] for v, _ in result) != sorted(canonical):
        raise ValueError("Present exactly the two canonical C4 container views")
    return result


def node_label(element, presentation, projection):
    kind = {"actor": "Persona", "external_system": "Sistema externo", "datastore": "Contenedor de datos", "container": "Contenedor"}[element["kind"]]
    technologies = technology_lines(element)
    if element["id"] == "postgresql_operational_store" and projection.combined_postgres:
        technologies = ["PostgreSQL / pgvector"]
    summary = presentation["node_summaries"][element["id"]]
    if element["id"] == "postgresql_operational_store" and projection.combined_postgres:
        summary += " y conocimiento RAG"
    rows = [f'<TR><TD><FONT POINT-SIZE="11">[{kind}]</FONT></TD></TR>',
            f'<TR><TD><FONT POINT-SIZE="16"><B>{lines(element["name"], 22)}</B></FONT></TD></TR>']
    if technologies:
        rows.append(f'<TR><TD><FONT POINT-SIZE="12">{lines(" · ".join(technologies), 27)}</FONT></TD></TR>')
    rows.append(f'<TR><TD><FONT POINT-SIZE="12">{lines(summary, 26)}</FONT></TD></TR>')
    return '<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="3">' + "".join(rows) + '</TABLE>>'


def route_geometry(view, relation):
    route = view["routes"][relation["id"]]
    def port(eid, side, offset):
        x, y = view["positions"][eid]
        return {"n": (x + offset, y + NODE_HEIGHT / 2), "s": (x + offset, y - NODE_HEIGHT / 2),
                "w": (x - NODE_WIDTH / 2, y + offset), "e": (x + NODE_WIDTH / 2, y + offset)}[side]
    return [port(relation["from"], route["from"], route.get("from_offset", 0)), *map(tuple, route["via"]),
            port(relation["to"], route["to"], route.get("to_offset", 0))]


def crosses_box(a, b, center):
    """Check whether a segment enters a non-endpoint node's open rectangle."""
    low, high = 0.0, 1.0
    for axis, half_size in ((0, NODE_WIDTH / 2 - 0.01), (1, NODE_HEIGHT / 2 - 0.01)):
        left, right = center[axis] - half_size, center[axis] + half_size
        delta = b[axis] - a[axis]
        if delta == 0:
            if not left < a[axis] < right:
                return False
        else:
            t1, t2 = sorted(((left - a[axis]) / delta, (right - a[axis]) / delta))
            low, high = max(low, t1), min(high, t2)
            if low >= high:
                return False
    return low < high


def edge_position(points):
    # Explicit straight cubic segments: no automatic routing across boxes.
    tip = points[-1]
    previous = points[-2]
    dx, dy = tip[0] - previous[0], tip[1] - previous[1]
    length = (dx * dx + dy * dy) ** 0.5
    if length < 8:
        raise ValueError("Insufficient arrowhead clearance")
    shortened = [*points[:-1], (tip[0] - dx / length * 8, tip[1] - dy / length * 8)]
    controls = [shortened[0]]
    for a, b in zip(shortened, shortened[1:]):
        controls.extend([(a[0] + (b[0] - a[0]) / 3, a[1] + (b[1] - a[1]) / 3),
                         (a[0] + 2 * (b[0] - a[0]) / 3, a[1] + 2 * (b[1] - a[1]) / 3), b])
    return f"e,{tip[0]},{tip[1]} " + " ".join(f"{x:.3f},{y:.3f}" for x, y in controls)


def generate_dot(presentation, architecture, view, projection):
    graph = Digraph(view["id"], comment="GENERATED — sources: model/c4_container_presentation.yml + model/architecture.yml")
    graph.attr(viewport="1920,1080,1,960,540", splines="true", overlap="true", notranslate="true",
               bgcolor="white", fontname="DejaVu Sans", outputorder="edgesfirst")
    graph.attr("node", fontname="DejaVu Sans", shape="box", style="rounded,filled", fixedsize="true",
               width=str(NODE_WIDTH / 72), height=str(NODE_HEIGHT / 72), margin="0.03", fontsize="16", penwidth="1.6")
    graph.attr("edge", fontname="DejaVu Sans", fontsize="14", color="#52647A", arrowsize="0.7", penwidth="1.4")
    graph.node("slide_title", projection.view["title"], pos="960,1040!", shape="plaintext", style="", width="24", height="0.5", fontsize="30")
    graph.node("slide_subtitle", f"Diseño propuesto · {projection.count} nodos · {len(projection.relationships)} relaciones · Numeración en flechas y leyenda", pos="960,995!", shape="plaintext", style="", width="24", height="0.4", fontsize="16")
    # Presentation-only frame. neato -n2 does not lay out cluster boundaries.
    graph.node("prototype_boundary", "", pos="880,545!", width=str(1130 / 72), height=str(810 / 72),
               shape="box", style="dashed,rounded", color="#2563EB", penwidth="1.4")
    graph.node("prototype_boundary_title", architecture["architecture"]["name"], pos="880,930!",
               shape="plaintext", style="", width="14", height="0.3", fontsize="16", fontcolor="#2563EB")
    positions = view["positions"]
    def add_node(target, element, outside=False):
        x, y = positions[element["id"]]
        attrs = {"fillcolor": "#EFF6FF", "color": "#2563EB", "fontcolor": "#172554"}
        if outside:
            attrs.update(fillcolor="#F1F5F9", color="#64748B", fontcolor="#334155", style="dashed,filled")
        if element["kind"] == "actor":
            attrs.update(shape="oval", style="filled")
        if element["kind"] == "datastore":
            attrs.update(shape="cylinder", fillcolor="#ECFDF5", color="#059669", fontcolor="#064E3B")
        tooltip = element["name"] + " | " + c4.description(element, {l["id"]: l for l in architecture["layers"]}, set())
        target.node(element["id"], node_label(element, presentation, projection), pos=f"{x},{y}!", tooltip=tooltip, **attrs)
    for e in projection.inside:
        add_node(graph, e)
    for e in projection.outside:
        add_node(graph, e, True)
    rows = ['<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="18"><B>Relaciones y protocolos</B></FONT></TD></TR>']
    for index, r in enumerate(projection.relationships, 1):
        number = f"{index:02d}"
        graph.edge(r["from"], r["to"], xlabel=number, id=r["id"],
                   tooltip=f"{number}: {r['label']} ({r['protocol']})",
                   pos=edge_position(route_geometry(view, r)), xlp=",".join(map(str, view["routes"][r["id"]]["label"])),
                   style={"sync": "solid", "async": "dashed", "event": "dotted", "governance": "dashed"}[r["style"]])
        action = presentation["relationship_labels"][r["id"]]
        rows.append(f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="15"><B>{number}</B> {lines(action, 36)}</FONT>'
                    f'<BR ALIGN="LEFT"/><FONT POINT-SIZE="12" COLOR="#52647A">{escape(r["protocol"])}</FONT></TD></TR>')
    legend = '<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="6" CELLPADDING="0">' + "".join(rows) + '</TABLE>>'
    graph.node("relation_legend", legend, pos="1700,560!", width="5.5", height="12.0", shape="plaintext", style="", fixedsize="false")
    footer = "Azul: prototipo · Gris: actores/sistemas externos · Verde: persistencia | Continua: síncrona · Discontinua: asíncrona · Punteada: evento"
    graph.node("slide_footer", footer, pos="960,85!", shape="plaintext", style="", width="25", height="0.4", fontsize="14")
    note = "PostgreSQL/pgvector: una instancia física. Azure OpenAI: API externa; familia GPT-4, modelo concreto sin fijar." if projection.combined_postgres else "Revisión humana dentro de Diagnostic & Recommendation Service. Actions publica el artifact mediante su propio workflow."
    graph.node("slide_note", note, pos="960,45!", shape="plaintext", style="", width="25", height="0.4", fontsize="15")
    return graph.source


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    presentation, architecture = load_models(MODEL)
    projections = prepare(presentation, architecture)
    if args.validate_only:
        print("C4 CONTAINER PRESENTATION VALIDATION PASSED")
        return
    guide = ["# C4 de contenedores para diapositivas", "",
             "Modelo de presentación: `model/c4_container_presentation.yml`. Arquitectura: `model/architecture.yml`.",
             "Se conserva la proyección C4 canónica: todos sus nodos, fronteras, relaciones, protocolos y estilos.",
             "PostgreSQL/pgvector conserva la agrupación de C4 2A; Human Review se proyecta en su contenedor padre.",
             "Los nombres y tecnologías completos permanecen en las cajas. Las flechas usan números y una leyenda lateral.",
             "SVG y PNG: 1920×1080, formato 16:9. Diseño propuesto, sin acreditar implementación.", ""]
    for view, projection in projections:
        source = ROOT / "build" / f"{view['id']}.dot"
        target = ROOT / "out" / f"{view['id']}.svg"
        source.parent.mkdir(exist_ok=True)
        target.parent.mkdir(exist_ok=True)
        source.write_text(generate_dot(presentation, architecture, view, projection), encoding="utf-8")
        for fmt in ("svg", "png"):
            subprocess.run(["neato", "-n2", "-T" + fmt, "-Gdpi=72", str(source), "-o", str(target.with_suffix("." + fmt))], check=True, cwd=ROOT)
        guide.extend([f"## {projection.view['title']}", "", f"[SVG]({view['id']}.svg) · [PNG]({view['id']}.png)", "",
                      view["narration"].strip(), "", "### Contenedores, actores y sistemas externos", "",
                      "| Nombre exacto | Tipo / frontera | Tecnologías | Responsabilidades del modelo |",
                      "|---|---|---|---|"])
        elements = {e["id"]: e for e in projection.inside + projection.outside}
        for e in elements.values():
            tech = technology_lines(e)
            if e["id"] == "postgresql_operational_store" and projection.combined_postgres:
                tech = ["PostgreSQL / pgvector"]
            responsibilities = e.get("responsibilities") or e.get("capabilities") or [e.get("responsibility", presentation["node_summaries"][e["id"]])]
            location = "externo al prototipo" if e in projection.outside else "dentro del prototipo"
            technology = ", ".join(tech) or ("No aplica" if e["kind"] == "actor" else e["name"])
            guide.append(f"| {e['name']} | {e['kind']} / {location} | {technology} | {', '.join(responsibilities)} |")
        guide.extend(["", "### Relaciones", "", "| Nº | Origen → destino | Relación completa | Protocolo | Estilo |", "|---|---|---|---|---|"])
        for index, r in enumerate(projection.relationships, 1):
            guide.append(f"| {index:02d} | {elements[r['from']]['name']} → {elements[r['to']]['name']} | {r['label']} | {r['protocol']} | {r['style']} |")
        guide.append("")
        print(f"generated: {target.relative_to(ROOT)} ({projection.count} nodes, {len(projection.relationships)} relationships)")
    (ROOT / "out/c4_expo_guia.md").write_text("\n".join(guide), encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except (KeyError, TypeError, ValueError, OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"C4 presentation failed: {error}") from error
