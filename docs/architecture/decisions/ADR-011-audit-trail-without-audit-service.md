Title: Audit trail without standalone audit_service
Status: Accepted
Date: 2026-10-03

## Decision

Remove standalone `audit_service`, sin crear un microservicio sustituto.

La auditoría funcional se conserva como capacidad transversal `audit_trail`,
con persistencia en `postgresql_operational_store` y correlación por `correlationId`.
Su alcance incluye generación de diagnósticos, uso de evidencias, revisión humana
y eventos de acceso y gobierno.

Azure Monitor/Application Insights complementan exclusivamente la observabilidad
técnica; no sustituyen el audit trail funcional persistido en PostgreSQL.

Human-in-the-Loop sigue siendo obligatorio: cada revisión humana debe registrar
al menos `diagnostic_id`, `reviewer`, `decision`, `timestamp` y `correlationId`.
Se conserva la capacidad de validar, corregir o rechazar diagnóstico y recomendación.

## Rationale

- La auditabilidad es transversal y no requiere un microservicio dedicado.
- Debe conservar trazabilidad de diagnósticos, evidencias y revisión humana.
- Reducir fronteras de servicio innecesarias.
- Separar auditoría funcional de observabilidad técnica.
