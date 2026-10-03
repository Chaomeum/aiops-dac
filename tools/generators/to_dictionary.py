#!/usr/bin/env python3
"""Compile the full data dictionary from the persistent-domain SSOT."""

from domain_model import ROOT, load_domain, main_guard, sql_type, write_generated


def cell(value):
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Sí" if value else "No"
    if isinstance(value, list):
        return "; ".join(cell(v) for v in value)
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def generate_dictionary(model):
    lines = ["<!-- GENERATED — DO NOT EDIT. SSOT: model/domain.yml -->",
             "# Diccionario de datos", "", f"Modelo: `{model['model_version']}`. Una instancia PostgreSQL; {len(model['entities'])} tablas.",
             "", "Los tipos enum se materializan en el schema propietario de cada tabla.",
             "FK significa constraint físico intra-schema; logical_ref significa ID sin FK física.", ""]
    for schema in model["schemas"]:
        lines.extend([f"## Schema `{schema['id']}`", "", schema["description_es"], "",
                      "Owners permitidos: " + ", ".join(schema["owner_containers"]) + ".", ""])
        for e in model["entities"]:
            if e["schema"] != schema["id"]:
                continue
            lines.extend([f"### `{e['schema']}.{e['table']}`", "", e["description_es"], "",
                          f"Owner: `{e['owner_container']}`. scope_basis: `{e['scope_basis']}`. status: `{e['status']}`.",
                          "", "Fuentes: " + ", ".join(e["source"]) + ".", ""])
            if e.get("retention_policy"):
                lines.extend(["Retención: 365 días (ADR-013), anclada en `created_at`; no hay purge jobs.", ""])
            if e.get("unique_constraints"):
                lines.extend(["Claves únicas compuestas: " + "; ".join("`(" + ", ".join(u["columns"]) + ")`" for u in e["unique_constraints"]) + ".", ""])
            if e.get("checks"):
                lines.extend(["Checks: " + "; ".join("`" + c["expression"] + "`" for c in e["checks"]) + ".", ""])
            if e.get("domain_constraints"):
                lines.extend(["Constraints complementarias: " + ", ".join(e["domain_constraints"]) + ".", ""])
            headers = ["Columna", "Tipo", "PK", "FK", "logical_ref", "Nullable", "Unique", "Enum", "Descripción", "Fuente", "Assumption"]
            lines.extend(["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"])
            for c in e["attributes"]:
                composite = ["(" + ", ".join(u["columns"]) + ")" for u in e.get("unique_constraints", []) if c["name"] in u["columns"]]
                unique = "Sí" if c["unique"] else ("Compuesto: " + "; ".join(composite) if composite else "No")
                values = [c["name"], sql_type(model, e, c), c["pk"], c.get("fk"), c.get("logical_ref"), c["nullable"], unique, c.get("enum"), c["description_es"], c.get("source", e["source"]), c["assumption"]]
                lines.append("| " + " | ".join(cell(v) for v in values) + " |")
            lines.append("")
    lines.extend(["## Enums", "", *[f"- `{e['id']}`: " + ", ".join(e["values"]) + "." for e in model["enums"]], "",
                  "## Decisiones de diseño", ""])
    # The authored decisions are copied, not reinterpreted by a renderer.
    decisions = (ROOT / "model/domain_decisions.md").read_text(encoding="utf-8")
    start = decisions.index("## DD-001")
    lines.append(decisions[start:].replace("## DD-", "### DD-").rstrip())
    lines.extend(["", "## Assumptions", ""])
    lines.extend(f"- **{a['id']}** ({a['status']}): {a['description_es']}" for a in model["assumptions"])
    lines.extend(["", "## Open Questions", ""])
    for q in model["open_questions"]:
        lines.append(f"- **{q['id']} / {q['topic']}** ({q['status']}): {q['description_es']}" + (" `embedding_dimension: null`." if "embedding_dimension" in q else ""))
    lines.extend(["", "## IA-only / inferred", ""])
    for e in model["entities"]:
        if e["scope_basis"] == "ia_only" or e["status"] == "inferred":
            lines.append(f"- `{e['schema']}.{e['table']}`: {e['scope_basis']} / {e['status']}. {e['description_es']} Fuentes: {', '.join(e['source'])}.")
    return "\n".join(lines)


def main():
    write_generated("out/diccionario_datos.md", generate_dictionary(load_domain()))


if __name__ == "__main__":
    raise SystemExit(main_guard(main))
