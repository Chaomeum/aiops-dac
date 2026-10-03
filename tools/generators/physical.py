#!/usr/bin/env python3
"""Render declared physical views without making architecture decisions."""

import base64
import json
import sys
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml
from diagrams import Cluster, Diagram, Edge, Node

try:
    from .icon_map import icon_for, fallback_icon_for
except ImportError:
    from icon_map import icon_for, fallback_icon_for


ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "model/architecture.yml"
OUTPUT = ROOT / "out"
EDGE_STYLES = {
    "sync": {"style": "solid", "color": "#334155"},
    "async": {"style": "dashed", "color": "#334155"},
    "event": {"style": "dotted", "color": "#334155"},
    "governance": {"style": "dashed", "color": "red"},
}


def wrapped(text, width=34):
    """Change only presentation whitespace, never the model's wording."""
    return "\n".join(textwrap.wrap(text, width, break_long_words=False, break_on_hyphens=False))


def embed_icons(svg_path):
    """Embed package PNGs to make the generated SVG portable.

    Graphviz normally emits absolute image paths, which browser image viewers
    cannot load. This is part of generation, not a manual artifact correction.
    """
    svg_ns = "http://www.w3.org/2000/svg"
    xlink_ns = "http://www.w3.org/1999/xlink"
    ET.register_namespace("", svg_ns)
    ET.register_namespace("xlink", xlink_ns)
    tree = ET.parse(svg_path)
    for image in tree.iter(f"{{{svg_ns}}}image"):
        key = f"{{{xlink_ns}}}href"
        path = Path(image.attrib[key])
        data = path.read_bytes()
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError(f"Expected a PNG icon: {path}")
        image.set(key, "data:image/png;base64," + base64.b64encode(data).decode("ascii"))
    tree.write(svg_path, encoding="utf-8", xml_declaration=True)


def index(items, description):
    result = {}
    for item in items:
        ident = item["id"]
        if ident in result:
            raise ValueError(f"Duplicate {description} ID: {ident}")
        result[ident] = item
    return result


def prepare(model):
    """Preflight every view before writing any artifacts."""
    elements = index(model["elements"], "element")
    layers = index(model["layers"], "layer")
    views = index(model["views"], "view")
    relations = index(model["relationships"], "relationship")
    limit = model["architecture"]["view_constraints"]["max_nodes_per_view"]
    if type(limit) is not int or limit < 1:
        raise ValueError("max_nodes_per_view must be a positive integer")
    memberships = {eid: set() for eid in elements}
    for vid, view in views.items():
        for eid in view["elements"]:
            if eid not in elements:
                raise ValueError(f"{vid}: unknown element {eid}")
            memberships[eid].add(vid)
    physical = sorted(
        (view for view in views.values() if view["kind"] == "physical"),
        key=lambda view: view["id"],
    )
    for view in physical:
        vid = view["id"]
        if Path(vid).name != vid or vid in {".", ".."}:
            raise ValueError(f"Unsafe view ID: {vid}")
        if not isinstance(view["title"], str) or not view["title"]:
            raise ValueError(f"{vid}: missing title")
        members = view["elements"]
        if len(members) > limit:
            raise ValueError(f"{vid}: {len(members)} architectural nodes exceed limit {limit}")
        if len(set(members)) != len(members):
            raise ValueError(f"{vid}: duplicate membership")
        if type(view["include_external"]) is not bool:
            raise ValueError(f"{vid}: include_external must be boolean")
        # No collapse schema is defined by this model. Refuse to interpret one.
        if view.get("collapse") not in (None, False, [], {}):
            raise ValueError(f"{vid}: collapse semantics are unspecified; cannot render safely")
        final = view.get("final") is True or view.get("status") == "final"
        for eid in members:
            element = elements[eid]
            if not element.get("name") or element.get("layer") not in layers:
                raise ValueError(f"{vid}/{eid}: missing name or declared layer")
            if not layers[element["layer"]].get("name"):
                raise ValueError(f"{vid}/{eid}: layer has no name")
            if element["kind"] == "external_system" and not view["include_external"]:
                raise ValueError(f"{vid}: external member {eid} conflicts with include_external=false")
            if final and element.get("status") == "open_question":
                raise ValueError(f"{vid}: final view contains open_question {eid}")
    for relation in relations.values():
        if relation["from"] not in elements or relation["to"] not in elements:
            raise ValueError(f"{relation['id']}: undeclared endpoint")
        if not relation.get("label") or not relation.get("protocol"):
            raise ValueError(f"{relation['id']}: missing label or protocol")
        if relation["style"] not in EDGE_STYLES:
            raise ValueError(f"{relation['id']}: unknown style {relation['style']}")
    return elements, layers, physical, sorted(relations.values(), key=lambda r: r["id"]), memberships


def legend(diagram):
    """Presentation-only sample edges; no architectural relationships."""
    # A plain subgraph keeps the only Clusters reserved for declared layers.
    from graphviz import Digraph

    sample = Digraph("legend")
    sample.attr("node", fixedsize="false", labelloc="c")
    for style, attrs in EDGE_STYLES.items():
        left, right = f"legend_{style}_from", f"legend_{style}_to"
        sample.node(left, label=style, shape="plaintext", width="0", height="0")
        sample.node(right, label="", shape="point", width="0.04", height="0.04")
        sample.edge(left, right, **attrs)
    diagram.dot.subgraph(sample)


def render(view, elements, layers, relationships, memberships, missing_icons):
    members = set(view["elements"])
    nodes = {}
    stubs = {}
    # For opposite flows, constrain ranks in one direction and route the return
    # below the nodes. Both arrows retain their actual model direction/style.
    selected = [r for r in relationships if r["from"] in members or r["to"] in members]
    directions = {(r["from"], r["to"]) for r in selected}
    ranked_pairs = set()
    with Diagram(
        view["title"], filename=str(OUTPUT / view["id"]),
        direction="LR", curvestyle="curved", outformat="svg", show=False,
        graph_attr={
            "splines": "spline", "nodesep": "0.8", "ranksep": "0.9",
            "pad": "0.4", "newrank": "true", "labelloc": "t",
        },
        node_attr={"fontname": "DejaVu Sans", "fontsize": "11"},
        edge_attr={"fontname": "DejaVu Sans", "fontsize": "9"},
    ) as diagram:
        for lid in sorted({elements[eid]["layer"] for eid in members}):
            with Cluster(layers[lid]["name"], graph_attr={"margin": "24"}):
                for eid in sorted(members):
                    element = elements[eid]
                    if element["layer"] != lid:
                        continue
                    icon = icon_for(element)
                    if icon:
                        nodes[eid] = icon(wrapped(element["name"]), nodeid=f"element_{eid}")
                    else:
                        missing_icons.add(eid)
                        nodes[eid] = fallback_icon_for(element)(
                            wrapped(element["name"]), nodeid=f"element_{eid}",
                        )
        for relation in selected:
            src, dst = relation["from"], relation["to"]
            if src not in members and dst not in members:
                continue
            outside = src if src not in members else dst if dst not in members else None
            if outside is not None and outside not in stubs:
                destinations = memberships[outside] - {view["id"]}
                label = (
                    f"continúa en\n{next(iter(destinations))}"
                    if len(destinations) == 1 else "continúa fuera de esta vista"
                )
                stubs[outside] = Node(
                    label, nodeid=f"stub_{outside}", labelloc="c", shape="note", style="dashed,filled",
                    color="#64748b", fillcolor="#f1f5f9", fontcolor="#475569",
                    fixedsize="false", width="2", height="0.5",
                )
            source = nodes[src] if src in members else stubs[src]
            target = nodes[dst] if dst in members else stubs[dst]
            routing = {}
            if (dst, src) in directions and src != dst:
                pair = frozenset((src, dst))
                if pair in ranked_pairs:
                    routing = {"constraint": "false", "tailport": "s", "headport": "s"}
                else:
                    routing = {"tailport": "e", "headport": "w", "minlen": "2"}
                    ranked_pairs.add(pair)
            source >> Edge(
                label=wrapped(relation["label"]) + f"\n({relation['protocol']})",
                tooltip=f"{relation['label']} ({relation['protocol']})",
                **EDGE_STYLES[relation["style"]],
                **routing,
            ) >> target
        legend(diagram)
    embed_icons(OUTPUT / f"{view['id']}.svg")


def main():
    missing_icons = set()
    try:
        with MODEL.open(encoding="utf-8") as stream:
            prepared = prepare(yaml.safe_load(stream))
        elements, layers, views, relationships, memberships = prepared
        # Report neutral package fallbacks without requiring local assets.
        missing_icons.update(
            eid for view in views for eid in view["elements"]
            if icon_for(elements[eid]) is None
        )
        OUTPUT.mkdir(parents=True, exist_ok=True)
        for view in views:
            render(view, elements, layers, relationships, memberships, missing_icons)
            print(f"generated: out/{view['id']}.svg")
    except (KeyError, TypeError, ValueError, OSError, RuntimeError) as error:
        print(f"Physical generation failed: {error}", file=sys.stderr)
        return 1
    finally:
        print("fallback_icons: " + json.dumps(sorted(missing_icons), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
