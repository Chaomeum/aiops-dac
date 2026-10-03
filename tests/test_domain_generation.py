"""Regression tests for ownership, lineage and generated persistence constraints."""

from copy import deepcopy
from pathlib import Path
import re
import sys
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/generators"))
from domain_validation import validate_domain
from to_dbml import generate_dbml
from to_dictionary import generate_dictionary
from to_er_d2 import generate_er
from to_sql import generate_extras


class DomainGenerationTests(unittest.TestCase):
    def setUp(self):
        self.model = yaml.safe_load((ROOT / "model/domain.yml").read_text())
        self.architecture = yaml.safe_load((ROOT / "model/architecture.yml").read_text())

    def entity(self, name):
        return next(e for e in self.model["entities"] if e["table"] == name)

    def column(self, table, name):
        return next(c for c in self.entity(table)["attributes"] if c["name"] == name)

    def rejected(self, fragment):
        errors = validate_domain(self.model, self.architecture)
        self.assertTrue(any(fragment in error for error in errors), errors)

    def test_approved_model_has_seventeen_valid_tables(self):
        self.assertEqual(validate_domain(self.model, self.architecture), [])
        self.assertEqual(len(self.model["entities"]), 17)

    def test_owners_cannot_write_another_schema(self):
        self.entity("incidents")["owner_container"] = "recommendation_service"
        self.rejected("does not respect declared schema ownership")

    def test_unknown_owner_is_rejected(self):
        self.entity("evidence_items")["owner_container"] = "invented_service"
        self.rejected("must exist in architecture.yml or be shared")

    def test_table_requires_primary_key(self):
        self.column("repositories", "id")["pk"] = False
        self.rejected("table has no PK")
        with self.assertRaisesRegex(ValueError, "table has no PK"):
            generate_er(self.model)

    def test_cross_schema_physical_fk_is_rejected(self):
        attr = self.column("diagnoses", "incident_id")
        attr["fk"] = attr.pop("logical_ref")
        self.rejected("physical cross-schema FK is prohibited")

    def test_nonexistent_relation_is_rejected(self):
        self.model["relationships"][0]["to"] = "ops.missing.id"
        self.rejected("relationship references nonexistent table/column")
        with self.assertRaisesRegex(ValueError, "nonexistent table"):
            generate_er(self.model)

    def test_excluded_tables_and_terminology_are_rejected(self):
        table = self.entity("repositories")
        for name in ("users", "root_causes", "event_store", "scanner_results", "read_database"):
            with self.subTest(name=name):
                table["table"] = name
                self.rejected("Excluded table")
        self.column("diagnoses", "probable_cause")["name"] = "root_cause"
        self.rejected("root_cause is prohibited")

    def test_embedding_scale_remains_open(self):
        self.column("knowledge_chunks", "embedding")["type"] = "vector(1536)"
        self.rejected("without a fixed dimension")

    def test_confidence_scale_cannot_be_closed(self):
        self.entity("diagnoses")["checks"].append({"name": "bad_scale", "expression": "confidence >= 0 AND confidence <= 1"})
        self.rejected("closed-scale CHECK")

    def test_pending_cannot_be_a_persisted_review_decision(self):
        next(e for e in self.model["enums"] if e["id"] == "HumanReviewDecision")["values"].append("PENDING")
        self.rejected("HumanReviewDecision: expected approved values")

    def test_knowledge_requires_provenance_and_excludes_evaluation(self):
        self.column("knowledge_chunks", "provenance")["nullable"] = True
        self.rejected("provenance is mandatory")
        self.entity("knowledge_documents")["source"].append("evaluation/reference_solutions")
        self.rejected("cannot cite evaluation")

    def test_traceability_requires_nonnullable_correlation(self):
        self.column("diagnosis_source_links", "correlation_id")["nullable"] = True
        self.rejected("correlation_id must not be nullable")
        self.entity("diagnosis_source_links")["attributes"] = [c for c in self.entity("diagnosis_source_links")["attributes"] if c["name"] != "correlation_id"]
        self.rejected("requires correlation_id")

    def test_open_questions_and_ia_only_are_not_promoted(self):
        self.model["open_questions"][0]["status"] = "confirmed"
        self.rejected("cannot be confirmed")
        self.entity("pipeline_access_grants")["status"] = "confirmed"
        self.rejected("must remain IA-only/inferred")

    def test_er_limit_is_enforced(self):
        self.model["entities"].extend([deepcopy(self.model["entities"][0]) for _ in range(2)])
        self.rejected("maximum is 18")
        with self.assertRaisesRegex(ValueError, "exceeds 18"):
            generate_er(self.model)

    def test_dbml_refs_are_only_physical_intra_schema(self):
        dbml = generate_dbml(self.model)
        refs = re.findall(r"^Ref \w+: (\w+)\.\w+\.\w+ > (\w+)\.\w+\.\w+$", dbml, re.M)
        self.assertEqual(len(refs), 12)
        self.assertTrue(all(source == target for source, target in refs))
        self.assertIn("Referencia lógica a knowledge.knowledge_chunks.id", dbml)
        self.assertIn("embedding vector ", dbml)
        self.assertNotIn("vector(1536)", dbml)

    def test_extras_protect_origin_and_append_only_diagnoses(self):
        sql = generate_extras(self.model)
        self.assertIn("WHERE role = 'ORIGIN'", sql)
        self.assertIn("DEFERRABLE INITIALLY DEFERRED", sql)
        self.assertIn("pe.failed IS NOT TRUE", sql)
        self.assertIn("BEFORE UPDATE OR DELETE OR TRUNCATE ON diagnosis.diagnoses", sql)
        self.entity("diagnoses")["domain_constraints"] = []
        self.rejected("missing approved domain constraints")

    def test_rag_traceability_cannot_be_removed(self):
        self.column("diagnosis_source_links", "knowledge_chunk_id").pop("logical_ref")
        self.rejected("required logical_ref to knowledge.knowledge_chunks.id")

    def test_dictionary_contains_all_fields_and_decisions(self):
        dictionary = generate_dictionary(self.model)
        for heading in ("Decisiones de diseño", "Assumptions", "Open Questions", "IA-only / inferred"):
            self.assertIn(f"## {heading}", dictionary)
        self.assertIn("diagnostic_id → diagnoses.id", dictionary)
        for entity in self.model["entities"]:
            for attr in entity["attributes"]:
                self.assertIn(f"| {attr['name']} |", dictionary)


if __name__ == "__main__":
    unittest.main()
