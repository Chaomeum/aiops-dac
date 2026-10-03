"""Check C4 boundaries and failure behaviour without rewriting artifacts."""

from copy import deepcopy
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import yaml


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "tools/generators/c4.py"
spec = importlib.util.spec_from_file_location("c4_generator", GENERATOR)
c4 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c4
spec.loader.exec_module(c4)
from tools.run_legacy_views import legacy_projection


class C4GenerationTests(unittest.TestCase):
    def setUp(self):
        self.model = yaml.safe_load((ROOT / "model/architecture.yml").read_text())
        self.elements = {e["id"]: e for e in self.model["elements"]}

    def projection(self, vid, model=None):
        projections, warnings = c4.prepare(model or self.model)
        return next(p for p in projections if p.view["id"] == vid), warnings

    def test_description_precedence_truncation_and_missing_basis(self):
        warnings = set()
        element = {"id": "test", "description": "A" * 100, "responsibility": "B",
                   "responsibilities": ["C"], "capabilities": ["D"], "layer": "layer"}
        layers = {"layer": {"purpose": "E"}}
        self.assertEqual(len(c4.description(element, layers, warnings)), 90)
        for field, expected in [("description", "B"), ("responsibility", "C"),
                                ("responsibilities", "D"), ("capabilities", "E")]:
            del element[field]
            self.assertEqual(c4.description(element, layers, warnings), expected)
        self.assertEqual(c4.description(element, {}, warnings), "")
        self.assertTrue(warnings)

    def test_technology_priority_and_null_handling(self):
        warnings = set()
        element = {"id": "test", "host": {"concrete_service": "Hosted"},
                   "technology": {"name": "Named"}, "provider": "Provider", "model": None}
        self.assertEqual(c4.technology(element, warnings), "Hosted")
        element["host"] = None
        self.assertEqual(c4.technology(element, warnings), "Named")
        element["technology"] = None
        self.assertEqual(c4.technology(element, warnings), "Provider")
        element["provider"] = None
        self.assertEqual(c4.technology(element, warnings), "")
        self.assertTrue(warnings)
        self.assertEqual(c4.technology(self.elements["web_dashboard"], warnings),
                         "React SPA / Azure Static Web Apps")
        self.assertEqual(c4.technology(self.elements["pretrained_llm_diagnostic_service"],
                                      warnings), "Azure OpenAI Service / GPT-4 family")

    def test_context_lifts_and_merges_by_direction(self):
        model = deepcopy(self.model)
        extra = deepcopy(model["relationships"][0])
        extra.update(id="extra", label="Third unique label", protocol="Additional protocol")
        model["relationships"].append(extra)
        projection, warnings = self.projection("c4_context", model)
        self.assertEqual(projection.count, 7)
        self.assertEqual([e["id"] for e in projection.inside], ["aiops"])
        outgoing = [r for r in projection.relationships
                    if (r["from"], r["to"]) == ("github_actions", "aiops")]
        self.assertEqual(len(outgoing), 1)
        self.assertNotIn("Third unique label", outgoing[0]["label"])
        self.assertIn("Additional protocol", outgoing[0]["protocol"])
        self.assertTrue(any(r["from"] == "aiops" and r["to"] == "github_actions"
                            for r in projection.relationships))
        self.assertTrue(any(r["from"] == "github" and r["to"] == "github_actions"
                            for r in projection.relationships))
        source = c4.generate_puml(model, projection, warnings)
        self.assertEqual(source.count("\nSystem("), 1)
        self.assertNotIn("\nContainer(", source)
        self.assertNotIn("\nComponent(", source)

    def test_processing_projects_one_physical_postgres(self):
        projection, warnings = self.projection("c4_container_processing")
        self.assertEqual(projection.count, 13)
        self.assertNotIn("pgvector_knowledge_store",
                         [e["id"] for e in projection.inside])
        vector_edge = next(r for r in projection.relationships if r["id"] == "rel_rag_pgvector")
        self.assertEqual(vector_edge["to"], "postgresql_operational_store")
        source = c4.generate_puml(self.model, projection, warnings)
        self.assertIn('"PostgreSQL / pgvector"', source)
        self.assertEqual(source.count("ContainerDb(postgresql_operational_store,"), 1)
        self.assertIn("System_Ext(pretrained_llm_diagnostic_service,", source)
        self.assertNotIn("Container(pretrained_llm_diagnostic_service,", source)
        self.assertFalse(any("derived_from" in r for r in projection.relationships))
        # Component persistence is lifted to the existing parent in Level 2.
        review = next(r for r in projection.relationships
                      if r["id"] == "rel_human_review_postgresql")
        self.assertEqual(review["from"], "recommendation_service")

    def test_component_boundary_and_derived_edges(self):
        projection, warnings = self.projection("c4_component_diagnostic")
        self.assertEqual(projection.count, 9)
        self.assertEqual(len(projection.inside), 4)
        self.assertTrue(all(e["parent"] == projection.view["container"]
                            for e in projection.inside))
        ids = {r["id"] for r in projection.relationships}
        self.assertIn("rel_apim_diagnostic_api", ids)
        self.assertIn("rel_human_review_postgresql", ids)
        self.assertNotIn("rel_apim_recommendation_service", ids)
        self.assertNotIn("rel_recommendation_service_postgresql", ids)
        source = c4.generate_puml(self.model, projection, warnings)
        self.assertIn('Container_Boundary(recommendation_service, '
                      '"Diagnostic & Recommendation Service")', source)
        self.assertEqual(source.count("  Component("), 4)
        self.assertEqual(source.count("\nContainer_Ext("), 3)
        self.assertEqual(source.count("\nContainerDb_Ext("), 1)
        self.assertEqual(source.count("\nSystem_Ext("), 1)

    def test_missing_or_unresolved_relationship_fields_fail(self):
        for field in ("label", "protocol"):
            for value in (None, "", "TBD"):
                with self.subTest(field=field, value=value):
                    model = deepcopy(self.model)
                    model["relationships"][0][field] = value
                    with self.assertRaisesRegex(ValueError, f"unresolved {field}"):
                        c4.prepare(model)

    def test_projection_limit_includes_context_neighbours(self):
        model = deepcopy(self.model)
        model["architecture"]["view_constraints"]["max_nodes_per_view"] = 6
        with self.assertRaisesRegex(ValueError, "7 nodes including stubs exceeds 6"):
            c4.prepare(model)

    def test_external_inclusion_and_final_context_are_enforced(self):
        model = deepcopy(self.model)
        model["views"][1]["include_external"] = False
        with self.assertRaisesRegex(ValueError, "include_external=false"):
            c4.prepare(model)
        model = deepcopy(self.model)
        model["views"][0]["final"] = True
        model["elements"][0]["status"] = "open_question"
        with self.assertRaisesRegex(ValueError, "final view contains open_question"):
            c4.prepare(model)

    def test_compiler_failure_preserves_exit_code_and_diagnostics(self):
        failure = subprocess.CompletedProcess([], 23, stdout="Compiler output", stderr="Bad syntax")
        with patch.object(c4.subprocess, "run", return_value=failure), \
                patch("sys.stderr", new_callable=io.StringIO) as stderr:
            self.assertEqual(c4.compile_svg([]), 23)
            self.assertIn("Compiler output", stderr.getvalue())
            self.assertIn("Bad syntax", stderr.getvalue())

    def test_sources_are_deterministic_across_hash_seeds(self):
        command = [
            sys.executable, "-c",
            "from tools.generators.c4 import *; "
            "model=yaml.safe_load(MODEL.read_text()); "
            "projections,warnings=prepare(model); "
            "print(''.join(generate_puml(model,p,warnings) for p in projections))",
        ]
        outputs = []
        for seed in ("1", "42"):
            result = subprocess.run(command, cwd=ROOT, env={**os.environ, "PYTHONHASHSEED": seed},
                                    capture_output=True, text=True, check=True, timeout=10)
            outputs.append(result.stdout)
        self.assertEqual(outputs[0], outputs[1])
        self.assertNotRegex(outputs[0], r"None|null|TBD")

    def test_legacy_projection_preserves_existing_review_and_model(self):
        original = deepcopy(self.model)
        legacy = legacy_projection(self.model)
        self.assertEqual(self.model, original)
        ids = {e["id"] for e in legacy["elements"]}
        self.assertIn("human_review_component", ids)
        self.assertNotIn("diagnostic_api_component", ids)
        relations = {r["id"] for r in legacy["relationships"]}
        self.assertIn("rel_recommendation_human_review", relations)
        self.assertIn("rel_human_review_postgresql", relations)
        self.assertNotIn("rel_output_postgresql", relations)
        self.assertTrue(all(r["from"] in ids and r["to"] in ids
                            for r in legacy["relationships"]))
        self.assertTrue(all(v["kind"] == "physical" for v in legacy["views"]))


if __name__ == "__main__":
    unittest.main()
