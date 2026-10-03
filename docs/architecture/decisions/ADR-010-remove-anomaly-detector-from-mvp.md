Title: Remove anomaly detector from MVP
Status: Accepted
Date: 2026-10-03

## Decision

Remove standalone `anomaly_detection_engine` from MVP, sin crear un nodo sustituto.

El prototipo parte de fallos ya identificados por GitHub Actions y concentra
el core en parsing, correlación de evidencia, RAG y diagnóstico asistido.
El flujo pasa directamente de `nlp_log_processor` a `evidence_correlation_engine`
mediante REST/HTTPS síncrono, entregando logs y evidencia procesada.

LogBERT queda fuera del MVP y puede evaluarse como extensión futura.
La detección de anomalías queda únicamente como posible extensión futura.
Se elimina OQ-001 y se retiran del modelo activo las referencias al detector,
incluidas INV-004 y CF-006, que dependían de su presencia en el MVP.

## Rationale

- GitHub Actions ya proporciona el estado fallido de la ejecución.
- El objetivo del prototipo es diagnosticar la causa probable del fallo, no detectar si ocurrió.
- Evitar un modelo adicional que no aporta valor directo al flujo crítico.
- Concentrar el MVP en correlación de evidencia, RAG y diagnóstico.
