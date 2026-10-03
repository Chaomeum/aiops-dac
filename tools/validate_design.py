#!/usr/bin/env python3
"""Validate class design against the unchanged architecture and domain SSOTs."""

from __future__ import annotations

from pathlib import Path
import re
import sys

import yaml

from domain_validation import validate_domain

ROOT = Path(__file__).resolve().parents[1]
IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PACKAGE = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
STEREOTYPES = {
    "Controller", "CommandService", "QueryService", "Aggregate", "Entity",
    "ValueObject", "DomainService", "Port", "Adapter", "Translator",
    "Repository", "Command", "Query", "Enum", "External",
}
RELATIONS = {"dispatches", "implements", "uses", "injects", "calls_http",
             "translates", "persists"}
DEPENDENCIES = {
    "interfaces": {"interfaces", "application"},
    "application": {"application", "domain"},
    "domain": {"domain"},
    "infrastructure": {"infrastructure", "application", "domain", "external"},
    "external": set(),
}
PACKAGES = {
    "interfaces": {"interfaces.rest"},
    "application": {"application.internal.commandservices",
                    "application.internal.queryservices",
                    "application.internal.outboundservices"},
    "domain": {"domain.model.aggregates", "domain.model.entities",
               "domain.model.valueobjects", "domain.model.commands",
               "domain.model.queries", "domain.model.events", "domain.services",
               "domain.exceptions"},
    "infrastructure": {"infrastructure.persistence.jpa", "infrastructure.clients",
                       "infrastructure.acl"},
}
ZOOMS = {"CD-1": "diagnostic_api_component",
         "CD-2": "diagnostic_orchestrator_component",
         "CD-3": "human_review_component"}
PERSISTED = {"Diagnosis": ("Aggregate", "diagnosis.diagnoses"),
             "Recommendation": ("Entity", "diagnosis.recommendations"),
             "HumanReview": ("Aggregate", "diagnosis.human_reviews")}
PRIMITIVES = {"UUID", "Instant", "String", "Object", "int", "long", "boolean",
              "void", "List", "Map", "Optional"}
JAVA_TYPES = {"uuid": "UUID", "uuid[]": "List<UUID>", "text": "String",
              "integer": "int", "bigint": "long", "boolean": "boolean",
              "timestamptz": "Instant", "jsonb": "Object"}
MINIMAL_RESULTS = {"void", "UUID", "String", "boolean", "int", "long"}
FORBIDDEN = re.compile(
    r"rootcause|eventsourc|eventstore|readdatabase|writedatabase|"
    r"auditservice|auditmicroservice|artifactpublisher|autonomousremediat|"
    r"autoremediat|applyfix|executefix|rollback|deploy", re.I)
FRAMEWORKS = re.compile(r"spring|jpa|hibernate|http|azure|fastapi|github|"
                        r"jackson|jsonnode|org\.|com\.azure", re.I)
UNSAFE_CONTENT = re.compile(r"rawlog|rawevidence|secret|credential|token|"
                            r"sensitivepayload", re.I)


def camel_case(value):
    first, *rest = value.split("_")
    return first + "".join(part[:1].upper() + part[1:] for part in rest)


def normalized(value):
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def load_models(paths):
    """Missing domain is a fatal precondition, including for direct invocation."""
    return tuple(yaml.safe_load(Path(path).read_text(encoding="utf-8"))
                 for path in paths)


def _validate(design, architecture, domain, root):
    errors = []
    if not isinstance(design, dict):
        return ["design.yml must contain a mapping"]
    domain_errors = validate_domain(domain, architecture)
    if domain_errors:
        return [f"domain precondition: {error}" for error in domain_errors]
    for field in ("model_version", "class_diagrams", "classes", "relationships",
                  "design_rules", "assumptions", "open_questions"):
        if field not in design:
            errors.append(f"design: missing {field}")
    for field in ("class_diagrams", "classes", "relationships", "assumptions",
                  "open_questions"):
        if not isinstance(design.get(field), list):
            errors.append(f"design.{field} must be a list")
        elif any(not isinstance(item, dict) for item in design[field]):
            errors.append(f"design.{field} must contain mappings")
    if errors:
        return errors
    if not isinstance(design["model_version"], str) or not design["model_version"].strip():
        errors.append("model_version must be a nonempty string")
    rules = design["design_rules"]
    expected_rules = {
        "container": "recommendation_service", "language": "Java",
        "framework": "Spring Boot", "max_nodes_per_diagram": 15,
        "cqrs": "logical", "persistence": "postgresql_operational_store",
        "event_sourcing": False, "separate_read_write_databases": False,
        "autonomous_remediation": False, "github_access": "read_only",
        "artifact_publisher": "github_actions",
        "navigation_views": ["c4_context", "c4_container_processing", "c4_component_diagnostic"],
    }
    for key, expected in expected_rules.items():
        if rules.get(key) != expected or type(rules.get(key)) is not type(expected):
            errors.append(f"design_rules.{key}: expected {expected!r}")

    elements = {item["id"]: item for item in architecture["elements"]}
    views = {item["id"]: item for item in architecture["views"]}
    arch_relations = {item["id"]: item for item in architecture["relationships"]}
    tables = {f"{item['schema']}.{item['table']}": item for item in domain["entities"]}
    enums = {item["id"]: item for item in domain["enums"]}
    if elements.get("recommendation_service", {}).get("backend") != {
            "language": "Java", "framework": "Spring Boot"}:
        errors.append("Java / Spring Boot must match architecture.yml")
    nav = expected_rules["navigation_views"]
    for index, vid in enumerate(nav):
        if vid not in views:
            errors.append(f"navigation: unknown architecture view {vid}")
        elif index and views[vid].get("zoom_from") != nav[index - 1]:
            errors.append(f"navigation: {vid} must zoom from {nav[index - 1]}")
    if views.get(nav[-1], {}).get("zoom_target") != "recommendation_service":
        errors.append("navigation: component view must target recommendation_service")

    classes = {}
    for item in design["classes"]:
        cid = item.get("id")
        if not isinstance(cid, str) or not IDENTIFIER.fullmatch(cid) or cid in classes:
            errors.append(f"invalid/duplicate class id: {cid!r}")
            continue
        classes[cid] = item
    names = [item.get("name") for item in classes.values()]
    if len(set(names)) != len(names):
        errors.append("class names must be unique")
    for cid, item in classes.items():
        for field in ("name", "package", "layer", "stereotype", "status",
                      "component_realized", "attributes", "methods"):
            if field not in item:
                errors.append(f"{cid}: missing {field}")
    if errors:
        return errors
    diagram_ids = [item.get("id") for item in design["class_diagrams"]]
    if diagram_ids != list(ZOOMS):
        errors.append("exactly CD-1, CD-2, CD-3 are required, in order")
    used = set()
    for diagram in design["class_diagrams"]:
        did, zoom = diagram.get("id"), diagram.get("zoom_target")
        members = diagram.get("elements", [])
        if not isinstance(members, list) or any(not isinstance(m, str) for m in members):
            errors.append(f"{did}: elements must be a list of class ids")
            continue
        used.update(members)
        if len(members) != len(set(members)):
            errors.append(f"{did}: duplicate members")
        if len(members) > min(15, architecture["architecture"]["view_constraints"]["max_nodes_per_view"]):
            errors.append(f"{did}: {len(members)} nodes exceeds maximum 15 (including proxies)")
        if not members or not diagram.get("title"):
            errors.append(f"{did}: title and members are required")
        if zoom not in elements or zoom != ZOOMS.get(did):
            errors.append(f"{did}: zoom_target must exist and match {ZOOMS.get(did)}")
        if zoom not in views.get(nav[-1], {}).get("elements", []):
            errors.append(f"{did}: zoom_target is not a declared C4 component view member")
        for cid in members:
            if cid not in classes:
                errors.append(f"{did}: unknown member {cid}")
    if used != set(classes):
        errors.append(f"unrendered/unknown classes: {sorted(used ^ set(classes))}")

    def owner(component):
        element = elements.get(component, {})
        return element.get("parent") if element.get("kind") == "component" else component

    def dependency(source, target, location):
        if target.get("layer") not in DEPENDENCIES.get(source.get("layer"), set()):
            errors.append(f"{location}: forbidden layer dependency "
                          f"{source.get('layer')} -> {target.get('layer')}")

    def check_types(item, type_name, location):
        if not isinstance(type_name, str) or not type_name.strip():
            errors.append(f"{location}: nonempty type required")
            return
        if item["layer"] == "domain" and FRAMEWORKS.search(type_name):
            errors.append(f"{location}: domain cannot import frameworks/provider types")
        for word in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", type_name):
            if word in classes:
                dependency(item, classes[word], location)
            elif word not in PRIMITIVES and word not in enums:
                errors.append(f"{location}: unknown type {word}")

    def protocol(reference, component, direction, location, target=None):
        canonical = arch_relations.get(reference.get("architecture_relationship"))
        if not canonical:
            errors.append(f"{location}: existing architecture_relationship required")
            return
        if reference.get("protocol") != canonical["protocol"]:
            errors.append(f"{location}: protocol must match architecture.yml ({canonical['protocol']})")
        endpoint = "to" if direction == "in" else "from"
        if canonical[endpoint] not in {component, owner(component)}:
            errors.append(f"{location}: architecture relationship endpoint differs from realized component")
        if target and canonical["to"] not in {target, owner(target)}:
            errors.append(f"{location}: architecture relationship target differs")

    for cid, item in classes.items():
        for field in ("name", "package", "layer", "stereotype", "status",
                      "component_realized", "attributes", "methods"):
            if field not in item:
                errors.append(f"{cid}: missing {field}")
        layer, package = item.get("layer"), item.get("package", "")
        stereotype, component = item.get("stereotype"), item.get("component_realized")
        if layer not in DEPENDENCIES:
            errors.append(f"{cid}: invalid layer {layer!r}")
        if not isinstance(package, str) or not PACKAGE.fullmatch(package):
            errors.append(f"{cid}: package is required and must be a Java-style namespace")
        elif layer != "external" and package not in PACKAGES.get(layer, set()):
            errors.append(f"{cid}: package {package!r} does not match layer/convention")
        if stereotype not in STEREOTYPES:
            errors.append(f"{cid}: invalid/missing stereotype {stereotype!r}")
        if stereotype != "External" and item.get("name") != cid:
            errors.append(f"{cid}: Java class name must match its identifier")
        if item.get("kind", "class") not in {"class", "interface", "enum"}:
            errors.append(f"{cid}: unsupported class kind")
        if component not in elements:
            errors.append(f"{cid}: component_realized must exist in architecture.yml")
        elif stereotype == "External":
            if layer != "external" or not package.startswith("external.") or item["attributes"] or item["methods"]:
                errors.append(f"{cid}: external proxy must have no internals")
            if component not in {"rag_retrieval", "pretrained_llm_diagnostic_service"}:
                errors.append(f"{cid}: undeclared external proxy")
        elif elements[component].get("kind") != "component" or owner(component) != "recommendation_service":
            errors.append(f"{cid}: internal classes must realize components of recommendation_service")
        if layer == "external" and stereotype != "External":
            errors.append(f"{cid}: external layer is only for graphical proxies")
        if stereotype in {"Port", "Repository"} and item.get("kind") != "interface":
            errors.append(f"{cid}: ports/repositories must be interfaces")
        if stereotype == "Enum" and item.get("kind") != "enum":
            errors.append(f"{cid}: Enum requires kind enum")
        if stereotype in {"Aggregate", "Entity", "DomainService", "Command", "Query", "Enum"} and layer != "domain":
            errors.append(f"{cid}: domain stereotype must live in domain")
        if stereotype in {"CommandService", "QueryService"} and layer != "application":
            errors.append(f"{cid}: application service must live in application")
        if stereotype == "Controller" and layer != "interfaces":
            errors.append(f"{cid}: controller must live in interfaces")
        if stereotype in {"Adapter", "Translator"} and layer != "infrastructure":
            errors.append(f"{cid}: adapters/translators must live in infrastructure")
        if cid.startswith("Jpa") and package != "infrastructure.persistence.jpa":
            errors.append(f"{cid}: JPA implementations must live in infrastructure.persistence.jpa")
        status = item.get("status")
        if status == "implemented":
            evidence = item.get("implementation", {})
            project = (root / evidence.get("service_root", "")).resolve()
            path = (root / evidence.get("path", "")).resolve()
            descriptors = [project / "pom.xml", project / "build.gradle", project / "build.gradle.kts"]
            if (evidence.get("container") != "recommendation_service"
                    or not project.is_relative_to(root.resolve()) or project == root.resolve()
                    or not path.is_relative_to(project) or path.suffix != ".java"
                    or not path.is_file()
                    or not re.search(r"\b(?:class|interface|enum|record)\s+" + re.escape(cid) + r"\b",
                                     path.read_text(encoding="utf-8"))
                    or not any(d.is_file() and "spring-boot" in d.read_text(encoding="utf-8")
                               for d in descriptors)):
                errors.append(f"{cid}: implemented requires real Java microservice code in this repository")
        elif status != "proposed":
            errors.append(f"{cid}: design status must be proposed (not inferred)")
        attributes, methods = item.get("attributes"), item.get("methods")
        if not isinstance(attributes, list) or not isinstance(methods, list):
            errors.append(f"{cid}: attributes/methods must be lists")
            continue
        if len({a.get("name") for a in attributes}) != len(attributes):
            errors.append(f"{cid}: duplicate attributes")
        for attribute in attributes:
            location = f"{cid}.{attribute.get('name')}"
            if not IDENTIFIER.fullmatch(attribute.get("name", "")):
                errors.append(f"{location}: invalid attribute name")
            check_types(item, attribute.get("type"), location)
        for method in methods:
            location = f"{cid}.{method.get('name')}"
            if not IDENTIFIER.fullmatch(method.get("name", "")):
                errors.append(f"{location}: invalid method name")
            check_types(item, method.get("returns"), location)
            if method.get("effect") not in {"read", "write", "pure"}:
                errors.append(f"{location}: explicit read/write/pure effect required")
            for param in method.get("parameters", []):
                check_types(item, param.get("type"), f"{location}/{param.get('name')}")
            if stereotype == "QueryService" and method.get("effect") == "write":
                errors.append(f"{location}: query service cannot modify state")
            if stereotype == "CommandService" and method.get("returns") not in MINIMAL_RESULTS:
                errors.append(f"{location}: command service must return void/minimal result")
        operational = {key: item.get(key) for key in
                       ("id", "name", "package", "attributes", "methods", "imports",
                        "values", "persisted_as", "persistence")}
        content = normalized(operational)
        if FORBIDDEN.search(content):
            errors.append(f"{cid}: prohibited design capability/name")
        if "github" in content and re.search(r"write|publish|upload|modify|push|delete|update|create", content):
            errors.append(f"{cid}: GitHub write adapter/operation prohibited")
        if layer == "domain" and FRAMEWORKS.search(" ".join(item.get("imports", []))):
            errors.append(f"{cid}: domain cannot import external frameworks")
        for imported in item.get("imports", []):
            imported_layer = imported.split(".")[0]
            if imported_layer in DEPENDENCIES:
                dependency(item, {"layer": imported_layer}, f"{cid}/import {imported}")
            elif layer == "domain" and not imported.startswith(("java.lang.", "java.util.", "java.time.")):
                errors.append(f"{cid}: domain cannot import external dependency {imported}")
        if layer != "external" and UNSAFE_CONTENT.search(content):
            errors.append(f"{cid}: raw/sensitive content prohibited in diagnostic design")
        if "persisted_as" in item:
            table = tables.get(item["persisted_as"])
            if not table:
                errors.append(f"{cid}: persisted_as must exist in domain.yml")
            else:
                expected = {a["name"]: a for a in table["attributes"]}
                actual = {a.get("domain_attribute") for a in attributes}
                if actual != set(expected) or len(attributes) != len(expected):
                    errors.append(f"{cid}: persisted attributes must exactly match domain.yml")
                for attr in attributes:
                    column = expected.get(attr.get("domain_attribute"))
                    if not column:
                        errors.append(f"{cid}: persisted attribute absent from domain.yml: {attr.get('name')}")
                        continue
                    java_type = column.get("enum") or JAVA_TYPES.get(column["type"])
                    if cid == "Diagnosis" and column["name"] == "probable_cause":
                        java_type = "ProbableCause"
                    if (attr["name"] != camel_case(column["name"])
                            or attr["type"] != java_type or attr.get("nullable") != column["nullable"]):
                        errors.append(f"{cid}.{attr['name']}: mapping/type/nullability differs from domain.yml")
                if table["owner_container"] != "recommendation_service":
                    errors.append(f"{cid}: aggregate/entity cannot own another context's table")
        if item.get("ingress"):
            protocol(item["ingress"], component, "in", f"{cid}/ingress")
        if item.get("persistence"):
            persistence = item["persistence"]
            protocol(persistence, component, "out", f"{cid}/persistence", persistence.get("store"))
            if layer != "infrastructure" or persistence.get("store") != rules["persistence"]:
                errors.append(f"{cid}: persistence must use common PostgreSQL in infrastructure")
            if not persistence.get("tables"):
                errors.append(f"{cid}: persistence.tables required")
            for table_name in persistence.get("tables", []):
                if table_name not in tables:
                    errors.append(f"{cid}: persistence target {table_name} absent from domain.yml")
                elif tables[table_name]["owner_container"] != "recommendation_service" and not (
                        cid == "PostgresAuditTrailAdapter" and table_name == "audit.audit_events"):
                    errors.append(f"{cid}: forbidden cross-context persistence")

    for cid, (stereotype, table_name) in PERSISTED.items():
        item = classes.get(cid, {})
        if (item.get("stereotype"), item.get("persisted_as")) != (stereotype, table_name):
            errors.append(f"{cid}: required {stereotype} persisted_as {table_name}")
    decision = classes.get("HumanReviewDecision", {})
    if (decision.get("stereotype") != "Enum"
            or decision.get("values") != enums["HumanReviewDecision"]["values"]):
        errors.append("HumanReviewDecision must be CONFIRMED|CORRECTED|REJECTED; PENDING is derived")
    view = classes.get("DiagnosticView", {})
    expected_view = elements["recommendation_service"]["diagnostic_output"]["includes"]
    if (view.get("role") != "read_model" or view.get("stereotype") != "ValueObject"
            or "persisted_as" in view
            or [a["name"] for a in view.get("attributes", [])] != [camel_case(a) for a in expected_view]):
        errors.append("DiagnosticView must be the nonpersisted application read model of diagnostic_output")
    context = classes.get("SanitizedDiagnosticContext", {})
    contract = elements["pretrained_llm_diagnostic_service"]["input_contract"]
    if ([a.get("contract_field") for a in context.get("attributes", [])] != contract
            or [a.get("name") for a in context.get("attributes", [])] != [camel_case(a) for a in contract]):
        errors.append("SanitizedDiagnosticContext must exactly represent the architecture LLM input_contract")
    gateway = classes.get("DiagnosticLlmGateway", {})
    if not gateway.get("methods") or any(
            [p.get("type") for p in m.get("parameters", [])] != ["SanitizedDiagnosticContext"]
            for m in gateway.get("methods", [])):
        errors.append("DiagnosticLlmGateway must accept only SanitizedDiagnosticContext")

    seen = set()
    for rel in design["relationships"]:
        src, dst, kind = rel.get("from"), rel.get("to"), rel.get("type")
        location = f"{src} -> {dst} ({kind})"
        if (src, dst, kind) in seen:
            errors.append(f"{location}: duplicate relationship")
        seen.add((src, dst, kind))
        if src not in classes or dst not in classes or kind not in RELATIONS:
            errors.append(f"{location}: unknown endpoint/type")
            continue
        source, target = classes[src], classes[dst]
        dependency(source, target, location)
        cross_context = owner(source["component_realized"]) != owner(target["component_realized"])
        if kind == "calls_http" or cross_context:
            protocol(rel, source["component_realized"], "out", location, target["component_realized"])
            if source["layer"] != "infrastructure" or target["stereotype"] != "External":
                errors.append(f"{location}: external HTTP calls belong to infrastructure adapters")
        if kind == "implements" and target.get("kind") != "interface":
            errors.append(f"{location}: implements target must be an interface")
        if kind == "persists" and (source["layer"] != "infrastructure"
                or target.get("persisted_as") not in source.get("persistence", {}).get("tables", [])):
            errors.append(f"{location}: persists must target a declared domain table from infrastructure")
        if kind == "dispatches" and (source["stereotype"] != "Controller"
                or target["stereotype"] not in {"CommandService", "QueryService"}):
            errors.append(f"{location}: controllers must dispatch to application services")
        method_map = {m["name"]: m for m in target["methods"]}
        for name in rel.get("methods", []):
            if name not in method_map:
                errors.append(f"{location}: unknown called method {name}")
        if source["stereotype"] == "QueryService" and kind != "implements":
            if target["stereotype"] in {"CommandService", "Port", "Adapter"} or kind == "persists":
                errors.append(f"{location}: query dependency may modify state")
            if target["stereotype"] == "Repository":
                if not rel.get("methods") or any(method_map.get(m, {}).get("effect") != "read"
                                                 for m in rel.get("methods", [])):
                    errors.append(f"{location}: query must select only read repository methods")
            elif any(method.get("effect") == "write" for name, method in method_map.items()
                     if not rel.get("methods") or name in rel["methods"]):
                errors.append(f"{location}: query cannot invoke mutating methods")
    for cid, item in classes.items():
        if item.get("kind") == "interface" and not any(
                r.get("type") == "implements" and r.get("to") == cid for r in design["relationships"]):
            errors.append(f"{cid}: interface has no proposed implementation")
    return errors


def validate_design(design, architecture, domain, root=ROOT):
    try:
        return _validate(design, architecture, domain, Path(root))
    except (KeyError, TypeError, AttributeError, ValueError, OSError) as exc:
        return [f"invalid design/source structure: {exc}"]


def main():
    defaults = [ROOT / "model/design.yml", ROOT / "model/architecture.yml", ROOT / "model/domain.yml"]
    paths = [Path(sys.argv[i + 1]) if len(sys.argv) > i + 1 else p for i, p in enumerate(defaults)]
    try:
        errors = validate_design(*load_models(paths))
    except (OSError, yaml.YAMLError) as exc:
        errors = [f"cannot load required SSOT: {exc}"]
    if errors:
        print("DESIGN VALIDATION FAILED\n" + "\n".join(f"- {e}" for e in errors))
        return 1
    print("DESIGN VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
