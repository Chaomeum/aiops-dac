"""Validate the persistent domain without changing any architectural facts."""

from pathlib import Path
import re
import sys

import yaml


IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
TYPES = {"uuid", "uuid[]", "text", "integer", "bigint", "boolean",
         "timestamptz", "jsonb", "vector", "numeric"}
EXCLUDED = {"users", "teams", "roles", "workflows", "failure_types",
            "root_causes", "reporting_service", "audit_service",
            "anomaly_detector", "anomaly_detection_engine", "logbert",
            "notifications", "credentials", "secrets", "event_store",
            "read_database", "write_database", "scanner_tables"}
REQUIRED_ENUMS = {
    "IncidentStatus": ["OPEN", "IN_REMEDIATION", "VERIFICATION", "RESOLVED"],
    "DiagnosisStatus": ["ANALYZING", "DIAGNOSIS_READY", "INCONCLUSIVE"],
    "HumanReviewDecision": ["CONFIRMED", "CORRECTED", "REJECTED"],
    "IncidentRunRole": ["ORIGIN", "VERIFICATION"],
    "PipelineStage": ["BUILD", "TESTING", "QUALITY_GATE", "DEPLOYMENT",
                      "CONTAINER", "INFRASTRUCTURE"],
    "MonitoringStatus": ["ACTIVE", "PAUSED"],
    "AccessCapability": ["VIEW", "OPERATE", "CONFIGURE"],
    "Severity": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
    "PipelineCriticality": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
}
TRACE_TABLES = {"pipeline_executions", "execution_stages", "incidents",
                "incident_runs", "pipeline_access_grants", "evidence_items",
                "correlated_contexts", "diagnoses", "recommendations",
                "diagnosis_evidence_links", "diagnosis_source_links",
                "human_reviews", "knowledge_documents", "knowledge_chunks",
                "audit_events"}


def validate_domain(domain, architecture):
    errors = []
    if not isinstance(domain, dict):
        return ["domain.yml must contain a mapping"]
    for section in ("schemas", "entities", "relationships", "enums",
                    "assumptions", "open_questions"):
        if not isinstance(domain.get(section), list):
            errors.append(f"domain.{section} must be a list")
    if errors:
        return errors
    if not domain.get("model_version"):
        errors.append("domain.model_version is required")

    elements = {e["id"]: e for e in architecture.get("elements", [])}
    def container(owner):
        if owner == "shared":
            return owner
        item = elements.get(owner, {})
        if item.get("kind") == "component":
            return item.get("parent")
        return owner if item.get("kind") == "container" else None

    schemas = {}
    for schema in domain["schemas"]:
        name = schema.get("id", "")
        if not IDENTIFIER.fullmatch(name) or name in schemas:
            errors.append(f"Invalid/duplicate schema: {name!r}")
        schemas[name] = schema
        owners = schema.get("owner_containers", [])
        if not owners or any(container(o) is None for o in owners):
            errors.append(f"{name}: invalid schema owner_containers")
    if set(schemas) != {"ops", "evidence", "diagnosis", "knowledge", "audit"}:
        errors.append("Expected approved schemas ops/evidence/diagnosis/knowledge/audit")

    enums = {e.get("id"): e for e in domain["enums"]}
    if len(enums) != len(domain["enums"]):
        errors.append("Duplicate domain enum")
    for name, values in REQUIRED_ENUMS.items():
        if enums.get(name, {}).get("values") != values:
            errors.append(f"{name}: expected approved values {values}")
    for name, enum in enums.items():
        if not isinstance(name, str) or not IDENTIFIER.fullmatch(name):
            errors.append(f"Invalid enum ID: {name!r}")
        if enum.get("schema") not in schemas:
            errors.append(f"{name}: unknown enum schema")
        values = enum.get("values", [])
        if not values or len(set(values)) != len(values):
            errors.append(f"{name}: invalid enum values")
    corpus = architecture_element(architecture, "rag_retrieval").get("knowledge_scope", [])
    if enums.get("KnowledgeCorpusKind", {}).get("values") != corpus:
        errors.append("KnowledgeCorpusKind must match authorized architecture knowledge_scope (INV-010)")
    if enums.get("AuditCategory", {}).get("values") != architecture.get("audit_trail", {}).get("scope", []):
        errors.append("AuditCategory must match architecture.audit_trail.scope")

    assumptions = {a.get("id") for a in domain["assumptions"]}
    if len(assumptions) != len(domain["assumptions"]):
        errors.append("Duplicate assumption ID")
    for question in domain["open_questions"]:
        if question.get("status") != "open_question":
            errors.append(f"{question.get('id')}: open_question must stay open; cannot be confirmed")
        if question.get("topic") == "embedding_dimension" and question.get("embedding_dimension", "missing") is not None:
            errors.append("embedding_dimension must remain null")
    topics = {q.get("topic") for q in domain["open_questions"]}
    required_topics = {"incident_severity_derivation", "confidence_semantics", "embedding_dimension",
                       "rag_corpus_updates", "pipeline_rbac", "monitored_workflow_registration"}
    if not required_topics <= topics:
        errors.append(f"Missing open questions: {sorted(required_topics - topics)}")

    entities = domain["entities"]
    if len(entities) > 18:
        errors.append(f"Domain has {len(entities)} tables; maximum is 18")
    tables, attributes, declared_refs = {}, {}, set()
    ids = set()
    for entity in entities:
        for field in ("id", "table", "schema", "owner_container", "description_es",
                      "scope_basis", "status", "source", "attributes"):
            if field not in entity:
                errors.append(f"{entity.get('id')}: missing {field}")
        schema, table = entity.get("schema"), entity.get("table", "")
        key = f"{schema}.{table}"
        if key in tables or entity.get("id") in ids:
            errors.append(f"Duplicate domain table/entity: {key}")
        ids.add(entity.get("id"))
        tables[key] = entity
        if not IDENTIFIER.fullmatch(table):
            errors.append(f"Invalid table identifier: {table!r}")
        if table.lower() in EXCLUDED or "scanner" in table.lower() or "root_cause" in table.lower():
            errors.append(f"Excluded table: {key}")
        owner = entity.get("owner_container")
        if container(owner) is None:
            errors.append(f"{key}: owner_container {owner!r} must exist in architecture.yml or be shared")
        allowed = schemas.get(schema, {}).get("owner_containers", [])
        if schema not in schemas or container(owner) not in allowed:
            errors.append(f"{key}: owner {owner!r} does not respect declared schema ownership")
        if entity.get("status") not in {"confirmed", "inferred"}:
            errors.append(f"{key}: persistent entity must be confirmed or inferred")
        if not entity.get("source"):
            errors.append(f"{key}: missing provenance source")
        if schema == "knowledge" and any(re.search(r"evaluat|reference_solution|solucion.*referencia", str(s), re.I)
                                          for s in entity.get("source", [])):
            errors.append(f"{key}: knowledge cannot cite evaluation as corpus provenance (INV-010)")
        if table == "pipeline_access_grants" and (entity.get("scope_basis") != "ia_only" or entity.get("status") != "inferred"):
            errors.append("pipeline_access_grants must remain IA-only/inferred")
        cols = entity.get("attributes", [])
        if not isinstance(cols, list):
            errors.append(f"{key}: attributes must be a list")
            continue
        if not any(c.get("pk") for c in cols):
            errors.append(f"{key}: table has no PK")
        names = {c.get("name") for c in cols}
        if len(names) != len(cols):
            errors.append(f"{key}: duplicate columns")
        if (table in TRACE_TABLES or entity.get("traceability_required")) and "correlation_id" not in names:
            errors.append(f"{key}: traceability table requires correlation_id")
        if entity.get("retention_policy") and "created_at" not in names:
            errors.append(f"{key}: retention requires created_at")
        for c in cols:
            location = f"{key}.{c.get('name')}"
            attributes[location] = c
            for field in ("name", "type", "pk", "nullable", "unique", "er_visible", "assumption", "description_es"):
                if field not in c:
                    errors.append(f"{location}: missing {field}")
            if not isinstance(c.get("name"), str) or not IDENTIFIER.fullmatch(c["name"]):
                errors.append(f"Invalid column: {location}")
            if "root_cause" in str(c.get("name", "")).lower():
                errors.append(f"{location}: root_cause is prohibited; use probable_cause")
            if c.get("type") not in TYPES:
                errors.append(f"{location}: unsupported type {c.get('type')!r}; embedding must be vector without dimension")
            for flag in ("pk", "nullable", "unique", "er_visible"):
                if type(c.get(flag)) is not bool:
                    errors.append(f"{location}: {flag} must be boolean")
            if c.get("pk") and c.get("nullable"):
                errors.append(f"{location}: PK cannot be nullable")
            if c.get("name") == "correlation_id" and c.get("nullable"):
                errors.append(f"{location}: correlation_id must not be nullable")
            if c.get("name") == "embedding" and c.get("type") != "vector":
                errors.append(f"{location}: embedding must use vector without a fixed dimension")
            if c.get("enum") and c["enum"] not in enums:
                errors.append(f"{location}: unknown enum {c['enum']}")
            if c.get("assumption") and c["assumption"] not in assumptions:
                errors.append(f"{location}: unknown assumption {c['assumption']}")
            if c.get("fk") and c.get("logical_ref"):
                errors.append(f"{location}: cannot declare both FK and logical_ref")
            for kind in ("fk", "logical_ref"):
                if c.get(kind):
                    declared_refs.add((location, c[kind], kind))
            if schema == "knowledge":
                # Inspect machine references, not descriptions explaining the prohibition.
                references = [c.get("fk", ""), c.get("logical_ref", ""), c.get("name", ""),
                              *c.get("source", [])]
                if any(re.search(r"evaluat|reference_solution|solucion.*referencia", r, re.I) for r in references):
                    errors.append(f"{location}: knowledge cannot reference evaluation (INV-010)")
        for constraint in entity.get("unique_constraints", []):
            if not constraint.get("columns") or not set(constraint["columns"]) <= names:
                errors.append(f"{key}: unique constraint references unknown columns")
        for check in entity.get("checks", []):
            if re.search(r"confidence", check.get("expression", ""), re.I):
                errors.append(f"{key}: confidence must not have a closed-scale CHECK")

    for src, target, kind in sorted(declared_refs):
        parts = target.split(".")
        if len(parts) != 3 or target not in attributes:
            errors.append(f"{src}: {kind} target does not exist: {target}")
            continue
        if kind == "fk" and src.split(".")[0] != parts[0]:
            errors.append(f"{src}: physical cross-schema FK is prohibited: {target}")
        source_type = attributes[src].get("type", "").removesuffix("[]")
        if source_type != attributes[target].get("type"):
            errors.append(f"{src}: reference type does not match {target}")
        if kind == "fk" and not (attributes[target].get("pk") or attributes[target].get("unique")):
            errors.append(f"{src}: FK target is not PK/unique: {target}")

    relationships, relation_ids = set(), set()
    for r in domain["relationships"]:
        rid = r.get("id")
        if not rid or rid in relation_ids:
            errors.append(f"Invalid/duplicate domain relationship ID: {rid}")
        relation_ids.add(rid)
        relationships.add((r.get("from"), r.get("to"), r.get("kind")))
        if r.get("from") not in attributes or r.get("to") not in attributes:
            errors.append(f"{rid}: relationship references nonexistent table/column")
    if relationships != declared_refs:
        errors.append("relationships must exactly match attribute FK/logical_ref declarations")
    for table in ("diagnoses", "human_reviews", "diagnosis_source_links", "knowledge_chunks"):
        if table not in ids:
            errors.append(f"Required entity missing: {table}")
    required_constraints = {
        "ops.incidents": {"exactly_one_failed_origin", "origin_pipeline_consistency"},
        "ops.incident_runs": {"at_most_one_origin"},
        "diagnosis.diagnoses": {"append_only"},
    }
    for table, required in required_constraints.items():
        actual = set(tables.get(table, {}).get("domain_constraints", []))
        if not required <= actual:
            errors.append(f"{table}: missing approved domain constraints {sorted(required - actual)}")
    expected_refs = {
        "diagnosis.diagnoses.incident_id": ("logical_ref", "ops.incidents.id"),
        "diagnosis.diagnosis_evidence_links.evidence_id": ("logical_ref", "evidence.evidence_items.id"),
        "diagnosis.diagnosis_source_links.knowledge_chunk_id": ("logical_ref", "knowledge.knowledge_chunks.id"),
        "knowledge.knowledge_chunks.document_id": ("fk", "knowledge.knowledge_documents.id"),
        "diagnosis.human_reviews.diagnostic_id": ("fk", "diagnosis.diagnoses.id"),
    }
    for column, (kind, target) in expected_refs.items():
        if attributes.get(column, {}).get(kind) != target:
            errors.append(f"{column}: required {kind} to {target}")
    for table in ("knowledge_documents", "knowledge_chunks"):
        if not any(c.get("name") == "provenance" and not c.get("nullable")
                   for c in tables.get(f"knowledge.{table}", {}).get("attributes", [])):
            errors.append(f"knowledge.{table}: provenance is mandatory (INV-010)")
    expected_owners = {"ops": "pipeline_service", "diagnosis": "recommendation_service",
                       "knowledge": "rag_retrieval", "audit": "shared"}
    for schema, expected in expected_owners.items():
        if schemas.get(schema, {}).get("owner_containers") != [expected]:
            errors.append(f"{schema}: approved schema owner must remain {expected}")
    for table, expected in (("evidence_items", "log_event_service"),
                            ("correlated_contexts", "evidence_correlation_engine")):
        if container(tables.get(f"evidence.{table}", {}).get("owner_container")) != expected:
            errors.append(f"evidence.{table}: approved table owner must remain {expected}")
    retention = domain.get("retention", {})
    if retention.get("duration_days") != architecture.get("retention", {}).get("duration_days"):
        errors.append("Domain retention must match architecture/ADR-013 (365 days)")
    return errors


def architecture_element(architecture, ident):
    return next((e for e in architecture.get("elements", []) if e.get("id") == ident), {})


def main():
    root = Path(__file__).resolve().parents[1]
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "model/domain.yml"
    arch = Path(sys.argv[2]) if len(sys.argv) > 2 else root / "model/architecture.yml"
    try:
        errors = validate_domain(yaml.safe_load(path.read_text()), yaml.safe_load(arch.read_text()))
    except (OSError, yaml.YAMLError, TypeError, KeyError, AttributeError) as exc:
        errors = [f"Cannot validate domain: {exc}"]
    if errors:
        print("DOMAIN VALIDATION FAILED\n" + "\n".join(f"- {e}" for e in errors))
        return 1
    print("DOMAIN VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
