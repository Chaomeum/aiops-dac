# Navegación C4 → diseño de clases

Modelo 1.0.0 — Diseño propuesto

SSOT: `model/design.yml`. Las figuras C4 existentes conservan su modelo y membresía.

## CD-1 — Diagnostic API y CQRS

[C4 Context (`c4_context`)](c4_context.svg) → [`c4_container_processing`](c4_container_processing.svg) → [`c4_component_diagnostic`](c4_component_diagnostic.svg) → `diagnostic_api_component` → [CD-1](CD-1.svg)

Zoom-In: `diagnostic_api_component`; 15 clases/nodos, incluidos proxies.

## CD-2 — Orquestación de Diagnóstico, RAG y LLM

[C4 Context (`c4_context`)](c4_context.svg) → [`c4_container_processing`](c4_container_processing.svg) → [`c4_component_diagnostic`](c4_component_diagnostic.svg) → `diagnostic_orchestrator_component` → [CD-2](CD-2.svg)

Zoom-In: `diagnostic_orchestrator_component`; 15 clases/nodos, incluidos proxies.

## CD-3 — Human Review y Gobierno Diagnóstico

[C4 Context (`c4_context`)](c4_context.svg) → [`c4_container_processing`](c4_container_processing.svg) → [`c4_component_diagnostic`](c4_component_diagnostic.svg) → `human_review_component` → [CD-3](CD-3.svg)

Zoom-In: `human_review_component`; 14 clases/nodos, incluidos proxies.

`diagnostic_output_component` se realiza dentro de CD-2 por `DiagnosticOutputComposer` y su dominio interno.

La vista `c4_component_diagnostic` amplía `recommendation_service` desde `c4_container_processing`.

Las clases compartidas de CD-1 son referencias al mismo diseño detallado en CD-2/CD-3; se cuentan en cada figura.
