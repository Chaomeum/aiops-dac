Title: Use existing backend through Azure API Management for Web Dashboard
Status: Accepted
Date: 2026-10-03

## Decision

Web Dashboard consumirá backend existente vía Azure API Management (REST/HTTPS): pipeline_service, log_event_service, recommendation_service, audit_service y reporting_service.

## Rationale

Reutilizar perímetro API aprobado y evitar duplicar backend.
