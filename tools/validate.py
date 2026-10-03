#!/usr/bin/env python3
import sys
from pathlib import Path
import yaml

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

for v in views:
    vid = v.get("id", "<unknown>")
    nodes = v.get("elements", v.get("nodes",
            v.get("include_elements", v.get("include", [])))) or []
    if len(nodes) > 15:
        errors.append(f"{vid}: {len(nodes)} nodes exceeds limit of 15")
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

if errors:
    print("ARCHITECTURE VALIDATION FAILED")
    print("\n".join(f"- {e}" for e in errors))
    sys.exit(1)

print("ARCHITECTURE VALIDATION PASSED")
