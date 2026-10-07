"""Physical synthesis must preserve hosting facts and portable approved icons."""

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from tools.generators import physical_presentation as renderer


class PhysicalPresentationTests(unittest.TestCase):
    def setUp(self):
        self.presentation, self.architecture = renderer.common.load_models(renderer.MODEL)
        self.elements = {e["id"]: e for e in self.architecture["elements"]}

    def test_projection_preserves_architecture_and_canonical_relations(self):
        before = deepcopy(self.architecture)
        _, projections = renderer.prepare(self.presentation, self.architecture)
        self.assertEqual(self.architecture, before)
        canonical = {r["id"]: r for r in self.architecture["relationships"]}
        for _, edges in projections:
            for edge in edges:
                self.assertEqual(edge["protocol"], canonical[edge["id"]]["protocol"])
                self.assertEqual(edge["style"], canonical[edge["id"]]["style"])
                self.assertNotIn("derived_from", edge)
        self.assertNotIn("pgvector_knowledge_store", self.presentation["collapse"])

    def test_runtime_details_differentiate_application_stack_from_managed_services(self):
        nlp = renderer.technology_lines(self.elements["nlp_log_processor"])
        self.assertEqual(nlp, ["Azure Container Apps", "Python / FastAPI", "Drain3"])
        diagnostic = renderer.technology_lines(self.elements["recommendation_service"])
        self.assertEqual(diagnostic, ["Azure Container Apps", "Java / Spring Boot"])
        for eid in ("entra_id", "api_management", "pretrained_llm_diagnostic_service", "web_dashboard"):
            self.assertNotIn("Azure Container Apps", renderer.technology_lines(self.elements[eid]))

    def test_does_not_invent_postgresql_host_or_concrete_llm(self):
        self.assertEqual(renderer.technology_lines(self.elements["postgresql_operational_store"]), [])
        self.assertEqual(renderer.technology_lines(self.elements["pgvector_knowledge_store"]), ["PostgreSQL / pgvector"])
        llm = self.elements["pretrained_llm_diagnostic_service"]
        self.assertEqual(llm["kind"], "external_system")
        self.assertIsNone(llm["model"])
        self.assertEqual(renderer.technology_lines(llm), ["Familia GPT-4"])

    def test_icons_are_installed_and_embedded_without_local_paths(self):
        fallbacks = set()
        attrs = renderer.node_attributes(self.elements["nlp_log_processor"], fallbacks)
        self.assertFalse(fallbacks)
        self.assertIn("container-apps.png", attrs["label"])
        icon = renderer.icon_for(self.elements["nlp_log_processor"])
        path = icon._load_icon(icon)
        with tempfile.TemporaryDirectory() as directory:
            svg = Path(directory) / "icon.svg"
            root = ET.Element("{http://www.w3.org/2000/svg}svg")
            ET.SubElement(root, "{http://www.w3.org/2000/svg}image", {
                "{http://www.w3.org/1999/xlink}href": path})
            ET.ElementTree(root).write(svg, encoding="utf-8")
            renderer.embed_icons(svg)
            data = svg.read_text()
            self.assertIn("data:image/png;base64,", data)
            self.assertNotIn(path, data)

    def test_rejects_wrong_view_kind_and_unknown_members(self):
        self.presentation["views"][0]["kind"] = "physical"
        with self.assertRaisesRegex(ValueError, "invalid kind"):
            renderer.prepare(self.presentation, self.architecture)
        self.presentation, _ = renderer.common.load_models(renderer.MODEL)
        self.presentation["views"][0]["elements"][0] = "invented_host"
        self.presentation["views"][0]["groups"][0]["elements"][0] = "invented_host"
        with self.assertRaisesRegex(ValueError, "unknown or explicitly collapsed"):
            renderer.prepare(self.presentation, self.architecture)


if __name__ == "__main__":
    unittest.main()
