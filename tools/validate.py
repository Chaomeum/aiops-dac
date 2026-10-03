#!/usr/bin/env python3
import sys
from pathlib import Path
import yaml
from domain_validation import validate_domain

FILE = Path(sys.argv[1] if len(sys.argv) > 1 else "model/architecture.yml")
errors = []

with FILE.open(encoding="utf-8") as f:
    doc = yaml.safe_load(f) or {}

elements = doc.get("elements", [])
relationships = doc.get("relationships", [])
views = doc.get("views", [])
outputs = doc.get("outputs", [])

element_ids = [e.get("id") for e in elements]
relation_ids = [r.get("id") for r in relationships]
view_ids = [v.get("id") for v in views if isinstance(v, dict) and v.get("id")]

all_ids = [x for x in element_ids + relation_ids + view_ids if x]
seen = set()
for ident in all_ids:
    if ident in seen:
        errors.append(f"Duplicate ID: {ident}")
    seen.add(ident)

known = set(x for x in element_ids if x)
used = set()
elements_by_id = {e.get("id"): e for e in elements if e.get("id")}
adjacency = {ident: set() for ident in known}

for r in relationships:
    rid = r.get("id", "<unknown>")
    src, dst = r.get("from"), r.get("to")
    if src not in known:
        errors.append(f"{rid}: unknown 'from': {src}")
    if dst not in known:
        errors.append(f"{rid}: unknown 'to': {dst}")
    if src in known:
        used.add(src)
    if dst in known:
        used.add(dst)
    if src in known and dst in known:
        adjacency[src].add(dst)
    if not r.get("label"):
        errors.append(f"{rid}: missing relationship label")
    if not r.get("protocol"):
        errors.append(f"{rid}: missing relationship protocol")
    if r.get("status") == "confirmed" and r.get("protocol") == "TBD":
        errors.append(f"{rid}: confirmed relationship has protocol TBD")
    if doc.get("open_questions") == [] and r.get("status") == "open_question":
        errors.append(f"{rid}: relationship is open_question but open_questions is empty")

for orphan in sorted(known - used):
    errors.append(f"Orphan element: {orphan}")

max_nodes = (doc.get("architecture", {}).get("view_constraints", {})
             .get("max_nodes_per_view", 15))
if type(max_nodes) is not int or max_nodes < 1:
    errors.append("architecture.view_constraints.max_nodes_per_view must be a positive integer")
    max_nodes = 15

for v in views:
    vid = v.get("id", "<unknown>")
    nodes = v.get("elements", v.get("nodes",
            v.get("include_elements", v.get("include", [])))) or []
    for eid in nodes:
        if eid not in known:
            errors.append(f"{vid}: unknown view element: {eid}")
    # Context projects internal endpoints onto one software system.
    context = v.get("kind") == "c4_context"
    if context and "elements" not in v:
        nodes = [eid for eid in element_ids
                 if eid in used and elements_by_id[eid].get("kind")
                 in {"actor", "external_system"}]
    node_count = len(nodes) + (1 if context else 0)
    if node_count > max_nodes:
        errors.append(f"{vid}: {node_count} nodes exceeds limit of {max_nodes}")
    if v.get("kind") == "c4_component":
        container = v.get("container")
        target = v.get("zoom_target")
        for field, ident in (("container", container), ("zoom_target", target)):
            if ident not in known or elements_by_id[ident].get("kind") != "container":
                errors.append(f"{vid}: {field} must reference a valid container: {ident!r}")
        if container in known and target in known and container != target:
            errors.append(f"{vid}: container and zoom_target must match")
        for eid in nodes:
            elem = elements_by_id.get(eid, {})
            if elem.get("kind") == "component":
                parent = elem.get("parent")
                if not parent:
                    errors.append(f"{vid}/{eid}: component has no parent")
                elif parent != container:
                    errors.append(
                        f"{vid}/{eid}: parent {parent!r} does not match "
                        f"boundary container {container!r}"
                    )
    final = v.get("final") is True or v.get("status") == "final"
    if final:
        for eid in nodes:
            elem = next((e for e in elements if e.get("id") == eid), None)
            if elem and elem.get("status") == "open_question":
                errors.append(f"{vid}: final view contains open_question: {eid}")

for e in elements:
    if e.get("kind") == "container" and str(e.get("layer")).upper() in {"5", "L5"}:
        if not e.get("host"):
            errors.append(f"{e.get('id')}: Layer 5 container has no host")
    if e.get("kind") == "component":
        eid = e.get("id", "<unknown>")
        parent = e.get("parent")
        if not parent:
            errors.append(f"{eid}: expected parent container ID; found parent={parent!r}")
        elif parent not in elements_by_id:
            errors.append(f"{eid}: expected existing parent container; found parent={parent!r}")
        elif elements_by_id[parent].get("kind") != "container":
            parent_kind = elements_by_id[parent].get("kind")
            errors.append(
                f"{eid}: expected parent kind container; "
                f"found parent={parent!r}, kind={parent_kind!r}"
            )


def has_directed_path(start, target):
    """Search publisher-to-producer paths without assuming any element IDs."""
    pending = [start]
    visited = set()
    while pending:
        current = pending.pop()
        if current == target:
            return True
        if current in visited:
            continue
        visited.add(current)
        pending.extend(adjacency.get(current, set()) - visited)
    return False


for output in outputs:
    oid = output.get("id", "<unknown>")
    producer = output.get("produced_by")
    publisher = output.get("published_by")
    if output.get("required") is True and not producer:
        errors.append(f"{oid}: required output missing produced_by")
    if "produced_by" in output and producer not in known:
        errors.append(f"{oid}: unknown produced_by: {producer!r}")
    if "published_by" in output and publisher not in known:
        errors.append(f"{oid}: unknown published_by: {publisher!r}")
    if (producer in known and publisher in known and producer != publisher
            and not has_directed_path(publisher, producer)):
        errors.append(
            f"{oid}: no directed path from published_by {publisher!r} "
            f"to produced_by {producer!r}"
        )

domain_path = Path(sys.argv[2]) if len(sys.argv) > 2 else FILE.with_name("domain.yml")
domain_checked = False
if domain_path.exists():
    domain_checked = True
    try:
        domain_errors = validate_domain(yaml.safe_load(domain_path.read_text(encoding="utf-8")), doc)
        errors.extend(f"domain: {e}" for e in domain_errors)
    except (OSError, yaml.YAMLError, TypeError, KeyError, AttributeError) as exc:
        errors.append(f"domain: cannot validate {domain_path}: {exc}")
elif len(sys.argv) > 2:
    errors.append(f"domain: model not found: {domain_path}")

if errors:
    print("ARCHITECTURE VALIDATION FAILED")
    print("\n".join(f"- {e}" for e in errors))
    sys.exit(1)

print("ARCHITECTURE VALIDATION PASSED")
if domain_checked:
    print("DOMAIN VALIDATION PASSED")
