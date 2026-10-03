#!/usr/bin/env python3
"""Render the single persistent-domain ER using D2 + ELK."""

import os
import subprocess

from domain_model import ROOT, find_tool, load_domain, main_guard, quote, write_generated


def visible_columns(entity):
    unique_columns = {c for u in entity.get("unique_constraints", []) for c in u["columns"]}
    return [c for c in entity["attributes"] if c["er_visible"] or c["pk"] or c.get("fk")
            or c.get("logical_ref") or c["unique"] or c.get("enum")
            or c["name"] == "correlation_id" or c["name"] in unique_columns]


def generate_er(model):
    # load_domain performs the shared checks before any generated file is written.
    if len(model["entities"]) > 18:
        raise ValueError("ER exceeds 18 tables")
    keys = {f"{e['schema']}.{e['table']}" for e in model["entities"]}
    for e in model["entities"]:
        if not any(c["pk"] for c in e["attributes"]):
            raise ValueError(f"{e['table']}: table has no PK")
    for r in model["relationships"]:
        if r["from"].rsplit(".", 1)[0] not in keys or r["to"].rsplit(".", 1)[0] not in keys:
            raise ValueError(f"{r['id']}: relationship points to nonexistent table")
    title = f"Modelo persistente — una instancia PostgreSQL / {len(model['entities'])} tablas"
    lines = ["# GENERATED — DO NOT EDIT. SSOT: model/domain.yml", "direction: down",
             f"title: {quote(title)} {{",
             "  shape: text", "  style.font-size: 26", "  near: top-center", "}", ""]
    colors = ["#DDEBF7", "#E2F0D9", "#FFF2CC", "#E4DDF5", "#E7E6E6"]
    for schema, color in zip(model["schemas"], colors):
        lines.extend([f"{schema['id']}: {quote(schema['id'])} {{", "  direction: right",
                      f"  style.fill: {quote(color)}"])
        for e in model["entities"]:
            if e["schema"] != schema["id"]:
                continue
            label = e["table"]
            lines.extend([f"  {e['table']}: {quote(label)} {{", "    shape: sql_table",
                          "    style.font-size: 15"])
            if e["scope_basis"] == "ia_only":
                lines.append("    style.stroke-dash: 2")
            unique_columns = {c for u in e.get("unique_constraints", []) for c in u["columns"]}
            cols = visible_columns(e)
            for c in cols:
                constraints = []
                if c["pk"]: constraints.append("primary_key")
                if c.get("fk"): constraints.append("foreign_key")
                if c.get("logical_ref"): constraints.append("ID lógico")
                if c["unique"]: constraints.append("unique")
                elif c["name"] in unique_columns: constraints.append("UQ compuesto")
                typ = c.get("enum", c["type"])
                row = f"    {c['name']}: {quote(typ)}"
                if constraints:
                    row += " {constraint: [" + "; ".join(quote(c) for c in constraints) + "]}"
                lines.append(row)
            hidden = len(e["attributes"]) - len(cols)
            if hidden:
                lines.append(f"    {quote('+' + str(hidden) + ' columnas')}: \"ver diccionario\"")
            lines.append("  }")
        lines.extend(["}", ""])
    for r in model["relationships"]:
        logical = r["kind"] == "logical_ref"
        label = "ref. lógica" if logical else "N:1"
        lines.append(f"{r['from']} -> {r['to']}: {quote(label)} {{")
        lines.extend(["  style.stroke-dash: 5" if logical else "  style.stroke-dash: 0",
                      '  style.stroke: "#586174"', "}"])
    lines.extend(["", 'legend: "Leyenda\\nLínea sólida: FK intra-schema (N:1)\\nLínea discontinua: ref. lógica por ID, sin FK física\\nBorde punteado: pipeline_access_grants (IA-only / inferred)\\nUQ compuesto: miembro de clave única compuesta\\n+N columnas: ver diccionario de datos\\nNo hay navegación ORM cross-context" {',
                  "  shape: text", "  style.font-size: 16", "  near: bottom-center", "}"])
    return "\n".join(lines)


def main():
    model = load_domain()
    write_generated("build/er.d2", generate_er(model))
    tool = find_tool("d2")
    env = dict(os.environ)
    if env.get("DEBUG") not in {None, "0", "1", "false", "true"}:
        env.pop("DEBUG")
    result = subprocess.run([str(tool), "--layout=elk", str(ROOT / "build/er.d2"),
                             str(ROOT / "out/er.svg")], cwd=ROOT,
                            capture_output=True, text=True, check=False, env=env)
    if result.returncode:
        raise RuntimeError("D2 failed: " + (result.stderr or result.stdout))
    if not (ROOT / "out/er.svg").is_file() or not (ROOT / "out/er.svg").stat().st_size:
        raise RuntimeError("D2 produced no/nonempty ER SVG")
    print("[domain] generated out/er.svg (D2 + ELK)")
    if result.stderr.strip():
        print(result.stderr.strip())


if __name__ == "__main__":
    raise SystemExit(main_guard(main))
