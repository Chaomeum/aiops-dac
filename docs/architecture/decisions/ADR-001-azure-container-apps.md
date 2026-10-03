Title: Use Azure Container Apps for backend containers
Status: Accepted
Date: 2026-10-03

## Context

El MVP utiliza contenedores backend en Microsoft Azure. La selección de su
plataforma de hosting estaba pendiente en OQ-004 — container_orchestrator;
`pipeline_service` y `log_event_service` ya estaban configurados con Azure
Container Apps. Actualmente no existe un requisito que obligue a administrar
directamente un clúster Kubernetes.

## Decision

Estandarizar el hosting de los contenedores backend del MVP en Azure Container
Apps. La decisión abarca `ingestion_normalization_service`,
`anomaly_detection_engine`, `evidence_correlation_engine`,
`recommendation_service`, `audit_service`, `reporting_service`,
`pipeline_service` y `log_event_service`.

`web_dashboard` queda fuera de esta decisión. La decisión cierra exclusivamente
OQ-004 — container_orchestrator.

## Rationale

El Architecture Owner aprobó esta decisión por los siguientes motivos:

- Integración nativa con el ecosistema Azure.
- Reducción de fricción de integración con el entorno corporativo existente.
- Aprovechamiento de controles nativos de gobierno y compliance de Azure.
- No existe actualmente un requisito que obligue a administrar directamente
  un clúster Kubernetes.

## Consequences

Los ocho contenedores backend comparten Azure Container Apps como plataforma
de hosting. Se conserva la propiedad `deployment.containerization.orchestrator`
por compatibilidad con el modelo actual, registrando la tecnología confirmada
y este ADR como fuente de la decisión.

El hosting del dashboard permanece pendiente. La selección del detector AIOps,
LLM, observabilidad, identidad, almacenamiento, parser y embeddings conserva
sus decisiones y preguntas abiertas existentes. Esta decisión no define otra
configuración de Azure Container Apps.
