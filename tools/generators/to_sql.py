#!/usr/bin/env python3
"""Export generated DBML using installed dbml2sql; add unexpressible constraints."""

import os
import re
import subprocess

from domain_model import ROOT, find_tool, load_domain, main_guard, write_generated
from to_dbml import generate_dbml


ORIGIN_CONSTRAINTS = """
-- DD-002: at most one ORIGIN, including concurrent writes.
CREATE UNIQUE INDEX incident_runs_one_origin_uq
ON ops.incident_runs (incident_id) WHERE role = 'ORIGIN';

-- DD-002: exactly one failed ORIGIN, consistent with the incident pipeline.
-- No extra workflow policy is imposed on VERIFICATION runs.
-- Deferred so incident + ORIGIN can be inserted in the same transaction.
CREATE FUNCTION ops.assert_incident_runs(p_incident uuid) RETURNS void
LANGUAGE plpgsql SET search_path = pg_catalog, ops AS $$
DECLARE
    p_pipeline uuid;
BEGIN
    SELECT pipeline_id INTO p_pipeline FROM ops.incidents
      WHERE id = p_incident FOR UPDATE;
    IF NOT FOUND THEN RETURN; END IF;
    IF (SELECT count(*) FROM ops.incident_runs
        WHERE incident_id = p_incident AND role = 'ORIGIN') <> 1 THEN
        RAISE EXCEPTION 'Incident % requires exactly one ORIGIN', p_incident
          USING ERRCODE = '23514';
    END IF;
    IF EXISTS (
        SELECT 1 FROM ops.incident_runs ir
        JOIN ops.pipeline_executions pe ON pe.id = ir.execution_id
        WHERE ir.incident_id = p_incident AND ir.role = 'ORIGIN' AND
          (pe.pipeline_id <> p_pipeline OR pe.failed IS NOT TRUE)
    ) THEN
        RAISE EXCEPTION 'Incident % requires a failed ORIGIN consistent with its pipeline', p_incident
          USING ERRCODE = '23514';
    END IF;
END;
$$;

CREATE FUNCTION ops.check_incident_runs() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, ops AS $$
DECLARE
    linked_incident uuid;
BEGIN
    IF TG_TABLE_NAME = 'incidents' THEN
        PERFORM ops.assert_incident_runs(NEW.id);
    ELSIF TG_TABLE_NAME = 'incident_runs' THEN
        IF TG_OP <> 'INSERT' THEN
            PERFORM ops.assert_incident_runs(OLD.incident_id);
        END IF;
        IF TG_OP <> 'DELETE' THEN
            PERFORM ops.assert_incident_runs(NEW.incident_id);
        END IF;
    ELSE
        FOR linked_incident IN SELECT incident_id FROM ops.incident_runs
            WHERE execution_id = NEW.id ORDER BY incident_id LOOP
            PERFORM ops.assert_incident_runs(linked_incident);
        END LOOP;
    END IF;
    RETURN NULL;
END;
$$;

CREATE CONSTRAINT TRIGGER incidents_origin_required
AFTER INSERT OR UPDATE ON ops.incidents DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION ops.check_incident_runs();

CREATE CONSTRAINT TRIGGER incident_runs_origin_required
AFTER INSERT OR UPDATE OR DELETE ON ops.incident_runs DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION ops.check_incident_runs();

CREATE CONSTRAINT TRIGGER execution_origin_stays_failed
AFTER UPDATE ON ops.pipeline_executions DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION ops.check_incident_runs();

-- TRUNCATE bypasses row/constraint triggers; reject it to preserve the invariant.
CREATE FUNCTION ops.reject_incident_runs_truncate() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Use transactional DELETE for incident run records'
      USING ERRCODE = '23514';
END;
$$;
CREATE TRIGGER incident_runs_no_truncate BEFORE TRUNCATE ON ops.incident_runs
FOR EACH STATEMENT EXECUTE FUNCTION ops.reject_incident_runs_truncate();
"""

APPEND_ONLY = """
-- DD-003: each status/content change creates a new immutable version.
-- Retention maintenance needs a future, explicitly controlled procedure; no purge job.
CREATE FUNCTION diagnosis.reject_diagnoses_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'diagnoses is append-only; insert a new version'
      USING ERRCODE = '23514';
END;
$$;
CREATE TRIGGER diagnoses_append_only
BEFORE UPDATE OR DELETE OR TRUNCATE ON diagnosis.diagnoses
FOR EACH STATEMENT EXECUTE FUNCTION diagnosis.reject_diagnoses_mutation();
"""


def generate_extras(model):
    constraints = {c for e in model["entities"] for c in e.get("domain_constraints", [])}
    supported = {"at_most_one_origin", "exactly_one_failed_origin", "origin_pipeline_consistency", "append_only"}
    if constraints - supported:
        raise ValueError(f"Unsupported domain constraints: {sorted(constraints - supported)}")
    parts = ["-- GENERATED — DO NOT EDIT. SSOT: model/domain.yml; DD-002 / DD-003."]
    origin = supported - {"append_only"}
    if constraints & origin:
        if not origin <= constraints:
            raise ValueError("ORIGIN constraints must be declared together")
        parts.append(ORIGIN_CONSTRAINTS)
    if "append_only" in constraints:
        parts.append(APPEND_ONLY)
    return "\n".join(parts)


def main():
    model = load_domain()
    dbml = ROOT / "model/db.dbml"
    if not dbml.exists() or dbml.read_text(encoding="utf-8") != generate_dbml(model).rstrip() + "\n":
        raise ValueError("DBML is stale; run make dbml before make sql")
    tool = find_tool("dbml2sql")
    env = {**os.environ, "PATH": str(tool.parent) + os.pathsep + os.environ.get("PATH", "")}
    result = subprocess.run([str(tool), str(dbml), "--postgres"], cwd=ROOT,
                            capture_output=True, text=True, env=env, check=False)
    if result.returncode:
        raise RuntimeError("dbml2sql failed: " + (result.stderr or result.stdout))
    sql = re.sub(r'^CREATE SCHEMA(?: IF NOT EXISTS)? "?[A-Za-z_][A-Za-z0-9_]*"?;\s*',
                 '', result.stdout, flags=re.M)
    preamble = ["-- GENERATED — DO NOT EDIT. model/domain.yml → model/db.dbml → dbml2sql.",
                *[f"CREATE SCHEMA IF NOT EXISTS {s['id']};" for s in model["schemas"]],
                "CREATE EXTENSION IF NOT EXISTS vector;", ""]
    write_generated("build/schema.sql", "\n".join(preamble) + sql)
    write_generated("build/extras.sql", generate_extras(model))
    print(f"[domain] SQL exporter: {tool}")


if __name__ == "__main__":
    raise SystemExit(main_guard(main))
