"""Check design invariants and compiler failures without changing source SSOTs."""

from copy import deepcopy
import io
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from validate_design import load_models, validate_design
from tools.generators import classes as generator


class DesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.design, cls.architecture, cls.domain = load_models([
            ROOT / "model/design.yml", ROOT / "model/architecture.yml", ROOT / "model/domain.yml"])

    def setUp(self):
        self.model = deepcopy(self.design)

    def item(self, cid):
        return next(c for c in self.model["classes"] if c["id"] == cid)

    def errors(self):
        return validate_design(self.model, self.architecture, self.domain)

    def rejected(self, fragment):
        self.assertIn(fragment, "\n".join(self.errors()))

    def test_approved_sources_and_exact_membership(self):
        self.assertEqual(self.errors(), [])
        self.assertEqual([len(d["elements"]) for d in self.model["class_diagrams"]], [15, 15, 14])
        for diagram in self.model["class_diagrams"]:
            source = generator.generate_puml(self.model, diagram)
            declarations = [line for line in source.splitlines()
                            if line.strip().startswith(("class ", "interface ", "enum "))]
            self.assertEqual(len(declarations), len(diagram["elements"]))
            for cid in diagram["elements"]:
                self.assertTrue(any(f" as {cid} <<" in line for line in declarations))
        self.assertIn('<<Aggregate>>', generator.generate_puml(self.model, self.model["class_diagrams"][1]))
        recommendations = next(r for r in self.model["relationships"]
                               if r["from"] == "Diagnosis" and r["to"] == "Recommendation")
        self.assertEqual(recommendations["multiplicity"], "0..*")

    def test_precondition_invalid_or_missing_domain(self):
        domain = deepcopy(self.domain)
        domain["enums"][2]["values"].append("PENDING")
        self.assertTrue(any("domain precondition" in e for e in
                            validate_design(self.model, self.architecture, domain)))
        with self.assertRaises(OSError):
            load_models([ROOT / "model/design.yml", ROOT / "model/architecture.yml", ROOT / "missing-domain.yml"])

    def test_fourth_diagram_and_node_limit_rejected(self):
        self.model["class_diagrams"].append({"id": "CD-4", "zoom_target": "diagnostic_output_component", "elements": []})
        self.rejected("exactly CD-1, CD-2, CD-3")
        self.model = deepcopy(self.design)
        self.model["class_diagrams"][1]["elements"].append("HumanReview")
        self.rejected("16 nodes exceeds maximum 15")

    def test_required_class_metadata_and_zoom(self):
        for field in ("package", "layer", "stereotype", "component_realized"):
            with self.subTest(field=field):
                self.model = deepcopy(self.design)
                del self.item("Diagnosis")[field]
                self.rejected(f"missing {field}")
        self.model = deepcopy(self.design)
        self.model["class_diagrams"][0]["zoom_target"] = "missing_component"
        self.rejected("zoom_target must exist")

    def test_table_names_and_exact_column_mapping(self):
        for cid in ("Diagnosis", "Recommendation", "HumanReview"):
            with self.subTest(cid=cid):
                self.model = deepcopy(self.design)
                self.item(cid)["attributes"].append({"name": "invented", "type": "String", "domain_attribute": "invented"})
                self.rejected("persisted attributes must exactly match")
        self.model = deepcopy(self.design)
        self.item("Diagnosis")["attributes"][1]["name"] = "incident_id"
        self.rejected("mapping/type/nullability differs")
        self.model = deepcopy(self.design)
        self.item("Diagnosis")["persisted_as"] = "diagnosis.unknown"
        self.rejected("persisted_as must exist")

    def test_persisted_type_nullability_and_decisions(self):
        self.item("Diagnosis")["attributes"][7]["type"] = "int"
        self.rejected("mapping/type/nullability differs")
        self.model = deepcopy(self.design)
        self.item("HumanReview")["attributes"][2]["nullable"] = True
        self.rejected("mapping/type/nullability differs")
        self.model = deepcopy(self.design)
        self.item("HumanReviewDecision")["values"].append("PENDING")
        self.rejected("CONFIRMED|CORRECTED|REJECTED")

    def test_layers_include_type_references_and_imports(self):
        self.model["relationships"].append({"from": "Diagnosis", "to": "JpaDiagnosisRepositoryAdapter", "type": "uses"})
        self.rejected("domain -> infrastructure")
        self.model = deepcopy(self.design)
        self.item("Diagnosis")["attributes"].append({"name": "client", "type": "AzureOpenAiDiagnosticAdapter"})
        self.rejected("domain -> infrastructure")
        for imported in ("org.springframework.stereotype.Service", "jakarta.persistence.Entity",
                         "infrastructure.clients.Client", "application.internal.commandservices.Service"):
            with self.subTest(imported=imported):
                self.model = deepcopy(self.design)
                self.item("Diagnosis")["imports"] = [imported]
                self.assertTrue(self.errors())

    def test_ports_are_interfaces_and_jpa_adapters_are_infrastructure(self):
        self.item("DiagnosisRepository")["kind"] = "class"
        self.rejected("ports/repositories must be interfaces")
        self.model = deepcopy(self.design)
        self.item("JpaDiagnosisRepositoryAdapter")["package"] = "domain.services"
        self.rejected("JPA implementations must live in infrastructure")

    def test_protocols_have_correct_canonical_endpoints(self):
        rel = next(r for r in self.model["relationships"] if r["type"] == "calls_http")
        del rel["protocol"]
        self.rejected("protocol must match architecture.yml")
        rel["protocol"] = "REST/HTTPS"
        rel["architecture_relationship"] = "rel_apim_diagnostic_api"
        self.rejected("endpoint differs")
        self.model = deepcopy(self.design)
        self.item("PostgresAuditTrailAdapter")["persistence"]["tables"] = ["knowledge.knowledge_documents"]
        self.rejected("forbidden cross-context persistence")

    def test_gateway_rejects_raw_content_and_other_parameters(self):
        for type_name in ("RawLog", "RawEvidence", "Secret", "Credential", "String"):
            with self.subTest(type_name=type_name):
                self.model = deepcopy(self.design)
                self.item("DiagnosticLlmGateway")["methods"][0]["parameters"][0]["type"] = type_name
                self.rejected("must accept only SanitizedDiagnosticContext")
        self.model = deepcopy(self.design)
        self.item("SanitizedDiagnosticContext")["attributes"].pop()
        self.rejected("must exactly represent the architecture LLM input_contract")

    def test_query_cannot_write_and_command_cannot_return_read_model(self):
        self.item("DiagnosisQueryServiceImpl")["methods"][0]["effect"] = "write"
        self.rejected("query service cannot modify state")
        self.model = deepcopy(self.design)
        rel = next(r for r in self.model["relationships"]
                   if r["from"] == "DiagnosisQueryServiceImpl" and r["to"] == "DiagnosisRepository")
        rel["methods"] = ["appendSnapshot"]
        self.rejected("query must select only read repository methods")
        self.model = deepcopy(self.design)
        self.item("GenerateDiagnosisCommandService")["methods"][0]["returns"] = "DiagnosticView"
        self.rejected("command service must return void/minimal result")

    def test_prohibited_capabilities_but_generic_publish_is_allowed(self):
        for name in ("RootCause", "EventStore", "AuditService", "AuditMicroservice",
                     "ArtifactPublisher", "AutoRemediation", "GitHubWriteAdapter", "GitHubUploadAdapter"):
            with self.subTest(name=name):
                self.model = deepcopy(self.design)
                self.item("LlmResponseTranslator")["name"] = name
                self.assertTrue(self.errors())
        self.model = deepcopy(self.design)
        self.item("GenerateDiagnosisCommandServiceImpl")["methods"].append({
            "name": "publishInternalEvent", "parameters": [], "returns": "void", "effect": "write"})
        self.assertEqual(self.errors(), [])

    def test_implemented_requires_real_microservice_not_renderer_code(self):
        item = self.item("Diagnosis")
        item["status"] = "implemented"
        item["implementation"] = {"container": "recommendation_service", "service_root": "tools", "path": "tools/validate.py"}
        self.rejected("implemented requires real Java microservice code")
        self.model = deepcopy(self.design)
        self.item("Diagnosis")["status"] = "inferred"
        self.rejected("design status must be proposed")

    def test_invalid_models_do_not_write_outputs(self):
        self.item("Diagnosis")["attributes"].clear()
        with patch.object(generator, "load_models", return_value=(self.model, self.architecture, self.domain)), \
                patch.object(generator, "compile_svgs") as compiler, \
                patch.object(Path, "write_text") as writer, \
                patch.object(sys, "argv", ["classes.py"]), patch("sys.stderr", new_callable=io.StringIO):
            self.assertEqual(generator.main(), 1)
            compiler.assert_not_called()
            writer.assert_not_called()

    def test_compiler_failure_is_reported(self):
        failure = subprocess.CompletedProcess([], 17, stdout="compile output", stderr="bad syntax")
        with patch.object(generator.subprocess, "run", return_value=failure):
            with self.assertRaisesRegex(ValueError, "PlantUML failed.*17"):
                generator.compile_svgs([])

    def test_no_empty_placeholder_text(self):
        for value in (None, "", "None", "null", "TBD"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                generator.literal(value)

    def test_deterministic_sources_across_hash_seeds_and_navigation_links(self):
        script = (
            "from tools.generators.classes import *; "
            "d,a,m=load_models([ROOT/'model/design.yml',ROOT/'model/architecture.yml',ROOT/'model/domain.yml']); "
            "print(''.join(generate_puml(d,v) for v in d['class_diagrams']))")
        outputs = [subprocess.run([sys.executable, "-c", script], cwd=ROOT,
                                  env={**os.environ, "PYTHONHASHSEED": seed}, capture_output=True,
                                  text=True, check=True, timeout=10).stdout for seed in ("1", "42")]
        self.assertEqual(*outputs)
        self.assertNotIn("linetype ortho", outputs[0])
        self.assertNotRegex(outputs[0], r"\b(?:None|null|TBD)\b")
        navigation = generator.navigation_markdown(self.model, self.architecture)
        for diagram in self.model["class_diagrams"]:
            self.assertIn(f"({diagram['id']}.svg)", navigation)
            self.assertIn(diagram["zoom_target"], navigation)


if __name__ == "__main__":
    unittest.main()
