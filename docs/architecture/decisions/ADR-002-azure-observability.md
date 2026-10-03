Title: Use Azure Monitor and Application Insights for observability
Status: Accepted
Date: 2026-10-03

## Decision

Usar Azure Monitor como plataforma de observabilidad y Application Insights
para telemetría de aplicación/APM del prototipo.

La decisión se registra en `observability_sources` y en
`deployment.observability_platform`, cierra OQ-005 — observability_platform
y actualiza el estado canónico de CF-010.

No modelar Log Analytics como nodo independiente.

## Rationale

Integración nativa con Azure y menor fricción con el entorno corporativo.
