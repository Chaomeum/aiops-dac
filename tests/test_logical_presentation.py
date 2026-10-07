"""Presentation projections must preserve canonical identity and boundaries."""

from copy import deepcopy
import unittest

from tools.generators import logical_presentation as renderer


class LogicalPresentationTests(unittest.TestCase):
    def setUp(self):
        self.presentation, self.architecture = renderer.load_models()

    def test_projection_preserves_source_and_external_identity(self):
        before = deepcopy(self.architecture)
        elements, projections = renderer.prepare(self.presentation, self.architecture)
        self.assertEqual(self.architecture, before)
        view, edges = projections[1]
        self.assertEqual(elements["pretrained_llm_diagnostic_service"]["kind"], "external_system")
        canonical = {r["id"]: r for r in self.architecture["relationships"]}
        for _, relationships in projections:
            for edge in relationships:
                self.assertEqual(edge["protocol"], canonical[edge["id"]]["protocol"])
                self.assertEqual(edge["style"], canonical[edge["id"]]["style"])
                self.assertNotIn("derived_from", edge)
        source = renderer.generate_dot(self.presentation, elements, view, edges)
        self.assertIn("Azure OpenAI API/HTTPS", source)

    def test_review_persistence_is_lifted_only_to_its_parent(self):
        _, projections = renderer.prepare(self.presentation, self.architecture)
        edges = projections[2][1]
        review = next(r for r in edges if r["id"] == "rel_human_review_postgresql")
        self.assertEqual(review["from"], "recommendation_service")
        self.assertEqual(review["to"], "postgresql_operational_store")
        self.assertTrue(all(r["from"] != r["to"] for r in edges))

    def test_rejects_collapse_into_another_service(self):
        self.presentation["collapse"]["human_review_component"] = "pipeline_service"
        with self.assertRaisesRegex(ValueError, "Invalid explicit component collapse"):
            renderer.prepare(self.presentation, self.architecture)

    def test_rejects_undeclared_relationship(self):
        self.presentation["relationship_labels"]["invented_flow"] = "Invented"
        with self.assertRaisesRegex(ValueError, "unknown relationships"):
            renderer.prepare(self.presentation, self.architecture)

    def test_rejects_hidden_membership_and_external_conflict(self):
        self.presentation["views"][0]["groups"][0]["elements"].append("entra_id")
        with self.assertRaisesRegex(ValueError, "partition declared membership"):
            renderer.prepare(self.presentation, self.architecture)
        self.presentation, _ = renderer.load_models()
        self.presentation["views"][0]["include_external"] = False
        with self.assertRaisesRegex(ValueError, "external member"):
            renderer.prepare(self.presentation, self.architecture)

    def test_rejects_incomplete_coverage_and_node_limit(self):
        self.presentation["views"] = self.presentation["views"][:2]
        with self.assertRaisesRegex(ValueError, "missing from presentation"):
            renderer.prepare(self.presentation, self.architecture)
        self.presentation, _ = renderer.load_models()
        self.architecture["architecture"]["view_constraints"]["max_nodes_per_view"] = 6
        with self.assertRaisesRegex(ValueError, "node limit"):
            renderer.prepare(self.presentation, self.architecture)


if __name__ == "__main__":
    unittest.main()
