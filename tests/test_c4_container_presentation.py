"""Slide adaptation must retain complete C4 semantics and fit its fixed canvas."""

from copy import deepcopy
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

from tools.generators import c4_container_presentation as renderer


class C4ContainerPresentationTests(unittest.TestCase):
    def setUp(self):
        self.presentation, self.architecture = renderer.load_models(renderer.MODEL)

    def test_complete_canonical_projection_is_preserved_without_source_mutation(self):
        before = deepcopy(self.architecture)
        adapted = renderer.prepare(self.presentation, self.architecture)
        originals, _ = renderer.c4.prepare(self.architecture)
        originals = {p.view["id"]: p for p in originals}
        self.assertEqual(self.architecture, before)
        self.assertEqual([(p.count, len(p.relationships)) for _, p in adapted], [(13, 18), (10, 12)])
        for view, projected in adapted:
            source = originals[view["source_view"]]
            self.assertEqual(projected.inside, source.inside)
            self.assertEqual(projected.outside, source.outside)
            self.assertEqual(projected.relationships, source.relationships)

    def test_no_undeclared_members_or_missing_routes(self):
        self.presentation["views"][0]["elements"].append("entra_id")
        with self.assertRaisesRegex(ValueError, "membership must exactly match"):
            renderer.prepare(self.presentation, self.architecture)
        self.presentation, _ = renderer.load_models(renderer.MODEL)
        del self.presentation["views"][0]["routes"]["rel_service_bus_nlp"]
        with self.assertRaisesRegex(ValueError, "every canonical relationship"):
            renderer.prepare(self.presentation, self.architecture)

    def test_rejects_flows_drawn_through_unrelated_nodes(self):
        self.presentation["views"][0]["routes"]["rel_nlp_correlation"]["via"] = [[450, 795]]
        with self.assertRaisesRegex(ValueError, "route crosses node"):
            renderer.prepare(self.presentation, self.architecture)

    def test_rejects_external_and_canvas_changes(self):
        self.presentation["views"][0]["include_external"] = False
        with self.assertRaisesRegex(ValueError, "include_external"):
            renderer.prepare(self.presentation, self.architecture)
        self.presentation, _ = renderer.load_models(renderer.MODEL)
        self.presentation["canvas"]["width"] = 1000
        with self.assertRaisesRegex(ValueError, "1920x1080"):
            renderer.prepare(self.presentation, self.architecture)

    def test_shared_postgresql_and_llm_identity_follow_canonical_projection(self):
        _, projected = renderer.prepare(self.presentation, self.architecture)[0]
        self.assertTrue(projected.combined_postgres)
        self.assertNotIn("pgvector_knowledge_store", {e["id"] for e in projected.inside})
        llm = next(e for e in projected.outside if e["id"] == "pretrained_llm_diagnostic_service")
        self.assertIsNone(llm["model"])
        self.assertNotIn("host", llm)
        for r in projected.relationships:
            if r["id"] == "rel_rag_pgvector":
                self.assertEqual(r["to"], "postgresql_operational_store")
            if r["id"] == "rel_human_review_postgresql":
                self.assertEqual(r["from"], "recommendation_service")

    def test_real_render_fits_16_9_preserves_all_names_and_edge_ids_without_overflow(self):
        ns = {"s": "http://www.w3.org/2000/svg"}
        with tempfile.TemporaryDirectory() as directory:
            for view, projected in renderer.prepare(self.presentation, self.architecture):
                dot = Path(directory) / f"{view['id']}.dot"
                dot.write_text(renderer.generate_dot(self.presentation, self.architecture, view, projected))
                for fmt in ("svg", "png"):
                    output = dot.with_suffix("." + fmt)
                    run = subprocess.run(["neato", "-n2", "-T" + fmt, "-Gdpi=72", str(dot), "-o", str(output)], capture_output=True, text=True)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertEqual(run.stderr, "", "Label overflow or routing warning")
                self.assertEqual(struct.unpack(">II", dot.with_suffix(".png").read_bytes()[16:24]), (1920, 1080))
                root = ET.parse(dot.with_suffix(".svg")).getroot()
                self.assertEqual(root.attrib["viewBox"], "0.00 0.00 1920.00 1080.00")
                edges = {g.attrib["id"] for g in root.findall(".//s:g[@class='edge']", ns)}
                self.assertEqual(edges, {r["id"] for r in projected.relationships})
                nodes = {g.find("s:title", ns).text: g for g in root.findall(".//s:g[@class='node']", ns)}
                self.assertIn("prototype_boundary", nodes)
                for e in projected.inside + projected.outside:
                    content = " ".join(t.text or "" for t in nodes[e["id"]].findall(".//s:text", ns))
                    self.assertIn(e["name"], content)


if __name__ == "__main__":
    unittest.main()
