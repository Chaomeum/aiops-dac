#!/usr/bin/env python3
"""Compile model/domain.yml to model/db.dbml; DBML is a generated artifact."""

from domain_model import (column_note, enum_definitions, load_domain, main_guard,
                          sql_type, write_generated)


def dbml_string(value):
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n") + "'"


def generate_dbml(model):
    lines = ["// GENERATED — DO NOT EDIT. SSOT: model/domain.yml",
             "Project aiops_persistent_domain {", "  database_type: 'PostgreSQL'",
             "  Note: 'ADR-018: una instancia PostgreSQL; CQRS lógico; sin Event Sourcing. Referencias cross-schema por ID sin FK física.'", "}", ""]
    for (schema, name), values in enum_definitions(model):
        lines.extend([f"Enum {schema}.{name} {{", *[f"  {value}" for value in values], "}", ""])
    for entity in model["entities"]:
        key = f"{entity['schema']}.{entity['table']}"
        lines.append(f"Table {key} {{")
        for attr in entity["attributes"]:
            settings = []
            if attr["pk"]:
                settings.append("pk")
            settings.append("null" if attr["nullable"] else "not null")
            if attr["unique"]:
                settings.append("unique")
            settings.append("note: " + dbml_string(column_note(entity, attr)))
            lines.append(f"  {attr['name']} {sql_type(model, entity, attr)} [{', '.join(settings)}]")
        if entity.get("unique_constraints"):
            lines.append("  indexes {")
            for constraint in entity["unique_constraints"]:
                cols = ", ".join(constraint["columns"])
                lines.append(f"    ({cols}) [unique, name: {dbml_string(constraint['name'])}]")
            lines.append("  }")
        if entity.get("checks"):
            lines.append("  checks {")
            for check in entity["checks"]:
                lines.append(f"    `{check['expression']}` [name: {dbml_string(check['name'])}]")
            lines.append("  }")
        note = f"{entity['description_es']} Owner: {entity['owner_container']}. {entity['scope_basis']} / {entity['status']}."
        if entity.get("domain_constraints"):
            note += " Constraints complementarias en extras.sql: " + ", ".join(entity["domain_constraints"]) + "."
        lines.extend(["  Note: " + dbml_string(note), "}", ""])
    for relationship in model["relationships"]:
        if relationship["kind"] == "fk":
            lines.append(f"Ref {relationship['id']}: {relationship['from']} > {relationship['to']}")
    lines.append("")
    for schema in model["schemas"]:
        lines.append(f"TableGroup {schema['id']} {{")
        lines.extend(f"  {e['schema']}.{e['table']}" for e in model["entities"] if e["schema"] == schema["id"])
        lines.extend(["}", ""])
    return "\n".join(lines)


def main():
    write_generated("model/db.dbml", generate_dbml(load_domain()))


if __name__ == "__main__":
    raise SystemExit(main_guard(main))
