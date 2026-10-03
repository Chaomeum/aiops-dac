"""Exercise the architecture validator through its command-line interface."""

from copy import deepcopy
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

import yaml


VALIDATOR = Path(__file__).resolve().parents[1] / "tools" / "validate.py"


def model_fixture():
    """Use unrelated IDs to ensure the artifact traversal is generic."""
    return {
        "elements": [
            {"id": "publisher", "kind": "external_system"},
            {"id": "gateway", "kind": "container", "layer": "L2"},
            {"id": "producer", "kind": "container", "layer": "L6"},
            {"id": "review", "kind": "component", "parent": "producer"},
        ],
        "relationships": [
            {"id": f"r{i}", "from": src, "to": dst,
             "label": "Calls", "protocol": "HTTPS", "status": "confirmed"}
            for i, (src, dst) in enumerate([
                ("publisher", "gateway"), ("gateway", "producer"),
                ("producer", "review"), ("review", "producer"),
            ])
        ],
        "outputs": [{"id": "artifact", "required": True,
                     "produced_by": "producer", "published_by": "publisher"}],
        "views": [],
        "open_questions": [],
    }


class ArchitectureValidationTests(unittest.TestCase):
    def setUp(self):
        self.model = model_fixture()

    def validate(self, model=None):
        with TemporaryDirectory() as directory:
            fixture = Path(directory) / "fixture.yml"
            fixture.write_text(yaml.safe_dump(model or self.model), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(VALIDATOR), str(fixture)],
                capture_output=True, text=True, timeout=10,
            )

    def assert_rejected(self, fragment, model=None):
        result = self.validate(model)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(fragment, result.stdout)

    def test_valid_parent_and_generic_multihop_path(self):
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_component_requires_parent(self):
        del self.model["elements"][3]["parent"]
        self.assert_rejected("review: expected parent container ID; found parent=None")

    def test_component_requires_existing_parent(self):
        self.model["elements"][3]["parent"] = "missing"
        self.assert_rejected("review: expected existing parent container; found parent='missing'")

    def test_component_parent_must_be_container(self):
        self.model["elements"][3]["parent"] = "publisher"
        self.assert_rejected("parent='publisher', kind='external_system'")

    def test_required_output_requires_producer(self):
        del self.model["outputs"][0]["produced_by"]
        self.assert_rejected("artifact: required output missing produced_by")

    def test_output_owners_must_exist(self):
        for field in ("produced_by", "published_by"):
            with self.subTest(field=field):
                model = deepcopy(self.model)
                model["outputs"][0][field] = "missing"
                self.assert_rejected(f"artifact: unknown {field}: 'missing'", model)

    def test_optional_output_publisher_must_exist(self):
        self.model["outputs"][0] = {"id": "artifact", "published_by": "missing"}
        self.assert_rejected("artifact: unknown published_by: 'missing'")

    def test_reverse_path_does_not_satisfy_artifact_path(self):
        self.model["relationships"][1].update({"from": "producer", "to": "gateway"})
        self.assert_rejected("no directed path from published_by 'publisher' to produced_by 'producer'")

    def test_unreachable_cycles_terminate(self):
        self.model["relationships"][1].update({"from": "gateway", "to": "publisher"})
        self.assert_rejected("no directed path")

    def test_same_producer_and_publisher_needs_no_path(self):
        self.model["outputs"][0]["published_by"] = "producer"
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_confirmed_tbd_protocol_is_rejected(self):
        self.model["relationships"][0]["protocol"] = "TBD"
        self.assert_rejected("r0: confirmed relationship has protocol TBD")

    def test_open_relationship_without_open_questions_is_rejected(self):
        self.model["relationships"][0]["status"] = "open_question"
        self.assert_rejected("r0: relationship is open_question but open_questions is empty")

    def test_open_relationship_with_open_questions_remains_allowed(self):
        self.model["relationships"][0].update({"status": "open_question", "protocol": "TBD"})
        self.model["open_questions"] = [{"id": "OQ-test"}]
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_existing_duplicate_endpoint_and_host_checks_remain(self):
        cases = []
        model = deepcopy(self.model)
        model["relationships"][1]["id"] = "r0"
        cases.append((model, "Duplicate ID: r0"))
        model = deepcopy(self.model)
        model["relationships"][0]["to"] = "missing"
        cases.append((model, "r0: unknown 'to': missing"))
        model = deepcopy(self.model)
        model["elements"][2]["layer"] = "L5"
        cases.append((model, "producer: Layer 5 container has no host"))
        for model, message in cases:
            with self.subTest(message=message):
                self.assert_rejected(message, model)

    def component_view(self):
        return {"id": "zoom", "kind": "c4_component", "container": "producer",
                "zoom_target": "producer", "elements": ["review", "gateway"],
                "final": False}

    def test_view_membership_must_reference_existing_elements(self):
        self.model["views"] = [{"id": "view", "elements": ["missing"]}]
        self.assert_rejected("view: unknown view element: missing")

    def test_node_limit_comes_from_architecture(self):
        self.model["architecture"] = {"view_constraints": {"max_nodes_per_view": 1}}
        self.model["views"] = [self.component_view()]
        self.assert_rejected("zoom: 2 nodes exceeds limit of 1")

    def test_component_zoom_requires_matching_existing_containers(self):
        cases = [
            ({"container": None}, "container must reference a valid container"),
            ({"zoom_target": "missing"}, "zoom_target must reference a valid container"),
            ({"container": "publisher"}, "container must reference a valid container"),
            ({"zoom_target": "gateway"}, "container and zoom_target must match"),
        ]
        for changes, message in cases:
            with self.subTest(changes=changes):
                model = deepcopy(self.model)
                model["views"] = [{**self.component_view(), **changes}]
                self.assert_rejected(message, model)

    def test_component_zoom_rejects_a_different_parent(self):
        self.model["views"] = [self.component_view()]
        self.model["elements"][3]["parent"] = "gateway"
        self.assert_rejected("parent 'gateway' does not match boundary container 'producer'")

    def test_final_c4_view_rejects_open_questions(self):
        self.model["views"] = [{**self.component_view(), "final": True}]
        self.model["elements"][3]["status"] = "open_question"
        self.assert_rejected("zoom: final view contains open_question: review")

    def test_context_counts_projected_system_and_external_nodes(self):
        self.model["architecture"] = {"view_constraints": {"max_nodes_per_view": 1}}
        self.model["views"] = [{"id": "context", "kind": "c4_context"}]
        self.assert_rejected("context: 2 nodes exceeds limit of 1")

    def test_final_context_checks_inferred_external_members(self):
        self.model["views"] = [{"id": "context", "kind": "c4_context", "final": True}]
        self.model["elements"][0]["status"] = "open_question"
        self.assert_rejected("context: final view contains open_question: publisher")


if __name__ == "__main__":
    unittest.main()
