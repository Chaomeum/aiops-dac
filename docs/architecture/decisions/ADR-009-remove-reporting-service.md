Title: Remove standalone reporting_service
Status: Accepted
Date: 2026-10-03

## Decision

Remove standalone `reporting_service`, sin crear un servicio sustituto.

La capacidad de reporte se conserva como `diagnostic_output`, un contrato
estructurado producido por el core AIOps y declarado en `recommendation_service`.
El dashboard consume el resultado mediante Azure API Management (REST/HTTPS).
GitHub Actions puede publicarlo como artifact mediante un paso nativo del workflow.
El formato concreto del artifact queda como detalle de implementación.
La autenticación GitHub App read-only permanece sin cambios ni permisos de escritura adicionales.

Esta ADR sustituye cualquier decisión previa de hosting o consumo que dependiera
específicamente de `reporting_service`; los ADRs históricos se conservan intactos.

## Rationale

- No aporta una capacidad analítica propia al core AIOps.
- Su responsabilidad era principalmente formatear información ya producida.
- Reducir componentes y fronteras innecesarias.
- Conservar el reporte como salida estructurada del diagnóstico.
