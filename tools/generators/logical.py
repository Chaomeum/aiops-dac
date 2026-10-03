#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

import yaml


# ============================================================================
# Paths
# ============================================================================

REPO_ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = REPO_ROOT / "model" / "architecture.yml"

BUILD_DIR = REPO_ROOT / "build"
OUT_DIR = REPO_ROOT / "out"

D2_OUTPUT = BUILD_DIR / "logica.d2"
SVG_OUTPUT = OUT_DIR / "logica.svg"


# ============================================================================
# Logical view configuration
# ============================================================================

# This order is intentionally different from the taxonomy L1..L8.
#
# It represents the architectural reading flow:
#
# External integrations
#       ↓
# Ingestion
#       ↓
# Event processing
#       ↓
# AIOps processing/correlation
#       ↓
# Assisted intelligence
#       ↓
# Persistence
#       ↓
# Governance
#       ↓
# Presentation/consumption
#
# architecture.yml remains the SSOT. This only changes the visual projection.
LOGICAL_LAYER_ORDER = [
    "L8",  # Integraciones Externas
    "L3",  # Ingesta y Normalización
    "L4",  # Procesamiento Orientado a Eventos
    "L5",  # Procesamiento y Correlación AIOps
    "L6",  # Inteligencia Asistida y Diagnóstico
    "L7",  # Persistencia y Evidencia
    "L2",  # Acceso, Seguridad y Gobierno
    "L1",  # Presentación y Consumo Operativo
]

# Edge labels are one of the main causes of excessive horizontal expansion.
# Wrapping only affects rendering; the canonical relationship labels remain
# untouched in architecture.yml.
EDGE_LABEL_WRAP_WIDTH = 38


# ============================================================================
# D2 helpers
# ============================================================================

SAFE_D2_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def d2_string(value: Any) -> str:
    """
    Return a safely quoted string for D2.

    json.dumps gives us deterministic escaping for:
    - quotes
    - backslashes
    - line breaks
    - UTF-8 characters

    ensure_ascii=False preserves Spanish accents in the generated D2.
    """
    return json.dumps(str(value), ensure_ascii=False)


def validate_d2_id(value: str, context: str) -> None:
    """
    Ensure an architecture identifier can safely be referenced as a D2 ID.

    Current architecture IDs such as:
        L5
        github_actions
        evidence_correlation_engine

    already comply with this restricted form.
    """
    if not SAFE_D2_ID.fullmatch(value):
        raise ValueError(
            f"Invalid D2 identifier {value!r} in {context}. "
            "Expected letters, numbers and underscores, starting with "
            "a letter or underscore."
        )


def node_shape(kind: str | None) -> str:
    """
    Map logical architecture element types to simple D2 shapes.

    This is a logical view, therefore cloud-provider icons are deliberately
    avoided. Those belong to the physical architecture.
    """
    shapes = {
        "actor": "person",
        "datastore": "cylinder",
        "external_system": "rectangle",
        "component": "rectangle",
        "container": "rectangle",
    }

    return shapes.get(kind or "", "rectangle")


def wrap_edge_label(
    label: str,
    protocol: str,
    width: int = EDGE_LABEL_WRAP_WIDTH,
) -> str:
    """
    Produce the mandatory combined relationship label:

        <action>
        (<protocol>)

    Long action descriptions are wrapped to prevent ELK from expanding the
    whole diagram horizontally.

    The protocol is always preserved exactly as declared in the model,
    including "TBD".
    """
    wrapped_action = "\n".join(
        textwrap.wrap(
            str(label),
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
        )
    )

    return f"{wrapped_action}\n({protocol})"


def edge_style_lines(style: str | None) -> list[str]:
    """
    Translate relationship semantics from architecture.yml to D2.

    sync
        Solid line. D2 default, so no style declaration is needed.

    async
        Dashed line.

    event
        Tighter dash pattern, visually approximating an event/dotted flow.

    governance
        Longer dashed line to distinguish a control/governance relationship
        from ordinary application traffic.
    """
    styles = {
        "sync": [],
        "async": [
            "style.stroke-dash: 5",
        ],
        "event": [
            "style.stroke-dash: 2",
        ],
        "governance": [
            "style.stroke-dash: 8",
        ],
    }

    return styles.get(style or "", [])


# ============================================================================
# Architecture model
# ============================================================================

def load_model() -> dict[str, Any]:
    """
    Load the canonical architecture model.
    """
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Architecture model not found: {MODEL_PATH}"
        )

    with MODEL_PATH.open("r", encoding="utf-8") as file:
        model = yaml.safe_load(file)

    if not isinstance(model, dict):
        raise ValueError(
            "architecture.yml must contain a YAML mapping at root."
        )

    required_sections = (
        "layers",
        "elements",
        "relationships",
    )

    for section in required_sections:
        if section not in model:
            raise ValueError(
                f"Required section {section!r} not found in "
                f"{MODEL_PATH.relative_to(REPO_ROOT)}."
            )

        if not isinstance(model[section], list):
            raise ValueError(
                f"Section {section!r} must be a YAML list."
            )

    return model


def build_indexes(
    model: dict[str, Any],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    """
    Validate the minimum structural contract needed by the logical renderer
    and create deterministic lookup maps.
    """
    layers_by_id: dict[str, dict[str, Any]] = {}
    elements_by_id: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Layers
    # ------------------------------------------------------------------

    for layer in model["layers"]:
        if not isinstance(layer, dict):
            raise ValueError(
                "Every entry under 'layers' must be a mapping."
            )

        layer_id = layer.get("id")

        if not layer_id:
            raise ValueError(
                "A layer without 'id' was found."
            )

        validate_d2_id(layer_id, "layers")

        if layer_id in layers_by_id:
            raise ValueError(
                f"Duplicate layer id: {layer_id}"
            )

        layers_by_id[layer_id] = layer

    # ------------------------------------------------------------------
    # Elements
    # ------------------------------------------------------------------

    for element in model["elements"]:
        if not isinstance(element, dict):
            raise ValueError(
                "Every entry under 'elements' must be a mapping."
            )

        element_id = element.get("id")
        layer_id = element.get("layer")

        if not element_id:
            raise ValueError(
                "An element without 'id' was found."
            )

        validate_d2_id(element_id, "elements")

        if element_id in elements_by_id:
            raise ValueError(
                f"Duplicate element id: {element_id}"
            )

        if not layer_id:
            raise ValueError(
                f"Element {element_id!r} does not define a layer."
            )

        if layer_id not in layers_by_id:
            raise ValueError(
                f"Element {element_id!r} references unknown "
                f"layer {layer_id!r}."
            )

        elements_by_id[element_id] = element

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    for relationship in model["relationships"]:
        if not isinstance(relationship, dict):
            raise ValueError(
                "Every entry under 'relationships' must be a mapping."
            )

        relationship_id = relationship.get(
            "id",
            "<unknown>",
        )

        source = relationship.get("from")
        target = relationship.get("to")
        label = relationship.get("label")
        protocol = relationship.get("protocol")

        if not source:
            raise ValueError(
                f"Relationship {relationship_id!r} has no 'from'."
            )

        if not target:
            raise ValueError(
                f"Relationship {relationship_id!r} has no 'to'."
            )

        if source not in elements_by_id:
            raise ValueError(
                f"Relationship {relationship_id!r} references "
                f"unknown source element {source!r}."
            )

        if target not in elements_by_id:
            raise ValueError(
                f"Relationship {relationship_id!r} references "
                f"unknown target element {target!r}."
            )

        if not label:
            raise ValueError(
                f"Relationship {relationship_id!r} has no label."
            )

        if not protocol:
            raise ValueError(
                f"Relationship {relationship_id!r} has no protocol."
            )

    return layers_by_id, elements_by_id


# ============================================================================
# Logical layout
# ============================================================================

def ordered_layers(
    model: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Return layers in logical-flow order.

    Important:
    This does NOT mutate architecture.yml.

    Any future layer not explicitly listed in LOGICAL_LAYER_ORDER is appended
    afterwards instead of silently disappearing from the generated view.
    """
    layers = model["layers"]

    layers_by_id = {
        layer["id"]: layer
        for layer in layers
    }

    result: list[dict[str, Any]] = []

    already_added: set[str] = set()

    for layer_id in LOGICAL_LAYER_ORDER:
        layer = layers_by_id.get(layer_id)

        if layer is not None:
            result.append(layer)
            already_added.add(layer_id)

    # Future-proofing: preserve any new canonical layer.
    for layer in layers:
        layer_id = layer["id"]

        if layer_id not in already_added:
            result.append(layer)
            already_added.add(layer_id)

    return result


def elements_for_layer(
    model: dict[str, Any],
    layer_id: str,
) -> list[dict[str, Any]]:
    """
    Preserve element ordering from architecture.yml while grouping by layer.
    """
    return [
        element
        for element in model["elements"]
        if element.get("layer") == layer_id
    ]


def element_reference(
    element_id: str,
    elements_by_id: dict[str, dict[str, Any]],
) -> str:
    """
    Elements are declared inside their corresponding D2 layer container.

    Therefore references must be fully qualified, e.g.:

        L8.github_actions
        L3.ingestion_normalization_service
        L5.evidence_correlation_engine
    """
    element = elements_by_id[element_id]
    layer_id = element["layer"]

    return f"{layer_id}.{element_id}"


# ============================================================================
# D2 source generation
# ============================================================================

def generate_d2(model: dict[str, Any]) -> str:
    """
    Generate a single logical D2 view from the canonical architecture model.
    """
    _, elements_by_id = build_indexes(model)

    architecture = model.get("architecture", {})

    architecture_name = architecture.get(
        "name",
        "Prototipo AIOps",
    )

    lines: list[str] = []

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    lines.extend(
        [
            "# ==================================================================",
            "# GENERATED FILE — DO NOT EDIT MANUALLY",
            "# Source: model/architecture.yml",
            "# Generator: tools/generators/logical.py",
            "# Layout: ELK",
            "# ==================================================================",
            "",
            "# Global reading direction:",
            "# top -> bottom",
            "direction: down",
            "",
            (
                "title: "
                + d2_string(
                    f"Arquitectura Lógica — {architecture_name}"
                )
                + " {"
            ),
            "  shape: text",
            "  near: top-center",
            "}",
            "",
        ]
    )

    # ------------------------------------------------------------------
    # Layers
    # ------------------------------------------------------------------

    for layer in ordered_layers(model):
        layer_id = layer["id"]
        layer_name = layer.get(
            "name",
            layer_id,
        )

        layer_elements = elements_for_layer(
            model,
            layer_id,
        )

        lines.append(
            f"{layer_id}: "
            f"{d2_string(f'{layer_id} — {layer_name}')} {{"
        )

        # Important compact-layout decision:
        #
        # Global architecture flows vertically,
        # but components inside each layer are arranged horizontally.
        lines.append("  direction: right")

        if not layer_elements:
            lines.append(
                "  # No architectural elements assigned to this layer"
            )

        for element in layer_elements:
            element_id = element["id"]
            element_name = element.get(
                "name",
                element_id,
            )

            kind = element.get("kind")
            shape = node_shape(kind)

            lines.append(
                f"  {element_id}: "
                f"{d2_string(element_name)} {{"
            )

            lines.append(
                f"    shape: {shape}"
            )

            lines.append("  }")

        lines.append("}")
        lines.append("")

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    lines.extend(
        [
            "# ==================================================================",
            "# Information flows",
            "# ==================================================================",
            "",
        ]
    )

    for relationship in model["relationships"]:
        relationship_id = relationship.get(
            "id",
            "relationship",
        )

        source_id = relationship["from"]
        target_id = relationship["to"]

        label = str(
            relationship["label"]
        )

        protocol = str(
            relationship["protocol"]
        )

        relation_style = str(
            relationship.get(
                "style",
                "sync",
            )
        )

        status = str(
            relationship.get(
                "status",
                "confirmed",
            )
        )

        source_ref = element_reference(
            source_id,
            elements_by_id,
        )

        target_ref = element_reference(
            target_id,
            elements_by_id,
        )

        # Required semantics:
        #
        # "<relationship action> (<protocol>)"
        #
        # Wrapped only for visualization.
        combined_label = wrap_edge_label(
            label=label,
            protocol=protocol,
        )

        lines.append(
            f"# {relationship_id}"
            f" | style={relation_style}"
            f" | status={status}"
        )

        style_lines = edge_style_lines(
            relation_style
        )

        if style_lines:
            lines.append(
                f"{source_ref} -> {target_ref}: "
                f"{d2_string(combined_label)} {{"
            )

            for style_line in style_lines:
                lines.append(
                    f"  {style_line}"
                )

            lines.append("}")

        else:
            lines.append(
                f"{source_ref} -> {target_ref}: "
                f"{d2_string(combined_label)}"
            )

        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ============================================================================
# Warnings
# ============================================================================

def collect_warnings(
    model: dict[str, Any],
) -> list[str]:
    """
    Surface unresolved rendering-relevant information without mutating it.

    A renderer must never silently replace TBD with an architectural decision.
    """
    warnings: list[str] = []

    for relationship in model["relationships"]:
        relationship_id = relationship.get(
            "id",
            "<unknown>",
        )

        protocol = relationship.get("protocol")
        status = relationship.get("status")

        if protocol == "TBD":
            warnings.append(
                f"{relationship_id}: protocol is TBD"
            )

        if status == "open_question":
            warnings.append(
                f"{relationship_id}: relationship status is open_question"
            )

    return warnings


# ============================================================================
# D2 rendering
# ============================================================================

def render_with_d2() -> None:
    """
    Compile build/logica.d2 to out/logica.svg using D2 + ELK.
    """
    d2_binary = shutil.which("d2")

    if not d2_binary:
        raise RuntimeError(
            "The 'd2' executable was not found in PATH. "
            "Install D2 or expose the executable before running "
            "the logical architecture generator."
        )

    command = [
        d2_binary,
        "--layout=elk",
        str(D2_OUTPUT),
        str(SVG_OUTPUT),
    ]

    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        details = (
            result.stderr.strip()
            or result.stdout.strip()
            or "No diagnostic output returned by D2."
        )

        raise RuntimeError(
            "D2 failed to render the logical architecture.\n"
            f"Command: {' '.join(command)}\n"
            f"{details}"
        )

    if not SVG_OUTPUT.exists():
        raise RuntimeError(
            "D2 finished successfully but the expected SVG "
            f"was not created: {SVG_OUTPUT}"
        )

    if SVG_OUTPUT.stat().st_size == 0:
        raise RuntimeError(
            f"D2 generated an empty SVG: {SVG_OUTPUT}"
        )


# ============================================================================
# Main
# ============================================================================

def main() -> int:
    try:
        model = load_model()

        # Validate the model subset required by this generator before writing
        # any generated artifact.
        build_indexes(model)

        BUILD_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        OUT_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        # ------------------------------------------------------------------
        # Generate D2
        # ------------------------------------------------------------------

        d2_source = generate_d2(model)

        D2_OUTPUT.write_text(
            d2_source,
            encoding="utf-8",
        )

        print(
            f"[logical] generated "
            f"{D2_OUTPUT.relative_to(REPO_ROOT)}"
        )

        # ------------------------------------------------------------------
        # Render SVG using ELK
        # ------------------------------------------------------------------

        render_with_d2()

        print(
            f"[logical] generated "
            f"{SVG_OUTPUT.relative_to(REPO_ROOT)}"
        )

        print(
            "[logical] layout=ELK "
            "| global_direction=down "
            "| layer_direction=right "
            f"| label_wrap={EDGE_LABEL_WRAP_WIDTH}"
        )

        # ------------------------------------------------------------------
        # Non-blocking warnings
        # ------------------------------------------------------------------

        warnings = collect_warnings(model)

        for warning in warnings:
            print(
                f"[logical] WARNING: {warning}",
                file=sys.stderr,
            )

        return 0

    except Exception as exc:
        print(
            f"[logical] ERROR: {exc}",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())