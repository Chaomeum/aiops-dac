# C4 de contenedores para diapositivas

Modelo de presentación: `model/c4_container_presentation.yml`. Arquitectura: `model/architecture.yml`.
Se conserva la proyección C4 canónica: todos sus nodos, fronteras, relaciones, protocolos y estilos.
PostgreSQL/pgvector conserva la agrupación de C4 2A; Human Review se proyecta en su contenedor padre.
Los nombres y tecnologías completos permanecen en las cajas. Las flechas usan números y una leyenda lateral.
SVG y PNG: 1920×1080, formato 16:9. Diseño propuesto, sin acreditar implementación.

## C4 Level 2A — Ingestion and AIOps Processing

[SVG](c4_expo_2a.svg) · [PNG](c4_expo_2a.png)

Las fuentes externas entregan evidencia a ingesta, que la protege antes del topic de Service Bus. Tres suscripciones alimentan Pipeline, Log/Event y NLP. NLP entrega evidencia a correlación y esta al servicio diagnóstico, que orquesta RAG e inferencia con Azure OpenAI. PostgreSQL/pgvector y Blob conservan datos y evidencias. La causa probable requiere revisión humana.

### Contenedores, actores y sistemas externos

| Nombre exacto | Tipo / frontera | Tecnologías | Responsabilidades del modelo |
|---|---|---|---|
| Ingestion and Normalization Service | container / dentro del prototipo | Azure Container Apps, Java / Spring Boot | authorized_capture, canonical_event_mapping, validation, parsing, cleaning, normalization, operational_noise_filtering, masking, anonymization, secret_filtering, data_minimization, correlation_id_assignment, evidence_metadata_capture |
| Azure Service Bus | container / dentro del prototipo | Azure Service Bus | persistent_asynchronous_messaging |
| Pipeline Service | container / dentro del prototipo | Azure Container Apps, Java / Spring Boot | register_pipeline, register_execution, maintain_pipeline_stages, maintain_execution_state, maintain_execution_metadata |
| Log/Event Service | container / dentro del prototipo | Azure Container Apps, Java / Spring Boot | register_normalized_evidence, query_logs_by_incident, query_events_by_incident, query_evidence_by_correlation_id, preserve_source_metadata, resolve_external_evidence_references |
| NLP Log Processing | container / dentro del prototipo | Azure Container Apps, Python / FastAPI, Drain3 | semantic_representation, log_preprocessing, signal_preparation |
| Evidence Correlation Service | container / dentro del prototipo | Azure Container Apps, Java / Spring Boot | Incident context |
| Diagnostic & Recommendation Service | container / dentro del prototipo | Azure Container Apps, Java / Spring Boot | generate_initial_recommendations, associate_recommendation_with_probable_cause, associate_recommendation_with_evidence, expose_evidence_limitations, orchestrate_diagnostic_flow |
| RAG Knowledge Retrieval | container / dentro del prototipo | Azure Container Apps, Python / FastAPI | retrieve_authorized_knowledge, semantic_search, preserve_provenance, interact_with_vector_store |
| PostgreSQL | datastore / dentro del prototipo | PostgreSQL / pgvector | pipelines, incidents, diagnoses, human_reviews, recommendations, metrics, audit_metadata, evidence_references, traceability_metadata |
| Evidence and Artifact Storage | datastore / dentro del prototipo | Azure Blob Storage | large_logs, technical_evidence, pipeline_artifacts, diagnostic_reports, historical_logs_when_authorized |
| GitHub Actions | external_system / externo al prototipo | GitHub Actions | ci_cd_execution_and_evidence_source |
| Compatible Observability and Runtime Sources | external_system / externo al prototipo | Azure Monitor, Application Insights | Authorized telemetry |
| Azure OpenAI Service | external_system / externo al prototipo | GPT-4 family | Inference via API |

### Relaciones

| Nº | Origen → destino | Relación completa | Protocolo | Estilo |
|---|---|---|---|---|
| 01 | GitHub Actions → Ingestion and Normalization Service | Emits authorized workflow events | HTTPS/Webhook | event |
| 02 | Azure Service Bus → Pipeline Service | Delivers execution events to register pipeline context | Azure Service Bus | async |
| 03 | Azure Service Bus → Log/Event Service | Delivers normalized evidence for registration and querying | Azure Service Bus | async |
| 04 | Pipeline Service → PostgreSQL | Persists pipelines, stages, states and execution metadata | PostgreSQL | sync |
| 05 | Log/Event Service → PostgreSQL | Persists and queries normalized evidence metadata and references | PostgreSQL | sync |
| 06 | Log/Event Service → Evidence and Artifact Storage | Stores and resolves references to large logs and evidence | Object Storage API | sync |
| 07 | Diagnostic & Recommendation Service → PostgreSQL | Persists diagnosis, recommendations and evidence links | PostgreSQL | sync |
| 08 | Ingestion and Normalization Service → GitHub Actions | Retrieves authorized logs, artifacts and metadata | GitHub API/HTTPS | sync |
| 09 | Ingestion and Normalization Service → Azure Service Bus | Publishes normalized and protected evidence | Azure Service Bus | async |
| 10 | Azure Service Bus → NLP Log Processing | Delivers normalized events for processing | Azure Service Bus | async |
| 11 | NLP Log Processing → Evidence Correlation Service | Delivers logs and processed evidence for correlation | REST/HTTPS | sync |
| 12 | Evidence Correlation Service → PostgreSQL | Records correlated context and traceability | PostgreSQL | sync |
| 13 | RAG Knowledge Retrieval → PostgreSQL | Retrieves semantically related operational knowledge | PostgreSQL/pgvector | sync |
| 14 | Compatible Observability and Runtime Sources → Ingestion and Normalization Service | Provides authorized telemetry and operational evidence | REST/HTTPS | sync |
| 15 | Evidence Correlation Service → Diagnostic & Recommendation Service | Delivers correlated incident context for assisted diagnosis | REST/HTTPS | sync |
| 16 | Diagnostic & Recommendation Service → RAG Knowledge Retrieval | Requests authorized contextual knowledge for the incident | REST/HTTPS | sync |
| 17 | Diagnostic & Recommendation Service → Azure OpenAI Service | Requests diagnostic inference with sanitized evidence and RAG context | Azure OpenAI API/HTTPS | sync |
| 18 | Diagnostic & Recommendation Service → PostgreSQL | Persists human review decisions and traceability | PostgreSQL | sync |

## C4 Level 2B — Consumption, Governance and Persistence

[SVG](c4_expo_2b.svg) · [PNG](c4_expo_2b.png)

El usuario accede al dashboard, se autentica con Entra ID y consume APIs protegidas por APIM. Pipeline, Log/Event y diagnóstico conservan los datos y la revisión humana en PostgreSQL; Log/Event administra evidencias en Blob. GitHub Actions consulta el diagnóstico mediante APIM y publica su artifact. La revisión pertenece al servicio diagnóstico, sin otro microservicio.

### Contenedores, actores y sistemas externos

| Nombre exacto | Tipo / frontera | Tecnologías | Responsabilidades del modelo |
|---|---|---|---|
| AIOps Web Dashboard | container / dentro del prototipo | Azure Static Web Apps, TypeScript / React, SPA | incident_query, diagnosis_query, evidence_query, recommendation_query, pipeline_status_query, tmd_metrics, comparative_diagnosis_metrics, human_review_registration, human_review_status_display, distinguish_generated_hypothesis_from_validated_diagnosis, role_protected_access |
| Azure API Management | container / dentro del prototipo | Azure API Management | protected_api_entry_point, request_routing, access_policy_enforcement |
| Pipeline Service | container / dentro del prototipo | Azure Container Apps, Java / Spring Boot | register_pipeline, register_execution, maintain_pipeline_stages, maintain_execution_state, maintain_execution_metadata |
| Log/Event Service | container / dentro del prototipo | Azure Container Apps, Java / Spring Boot | register_normalized_evidence, query_logs_by_incident, query_events_by_incident, query_evidence_by_correlation_id, preserve_source_metadata, resolve_external_evidence_references |
| Diagnostic & Recommendation Service | container / dentro del prototipo | Azure Container Apps, Java / Spring Boot | generate_initial_recommendations, associate_recommendation_with_probable_cause, associate_recommendation_with_evidence, expose_evidence_limitations, orchestrate_diagnostic_flow |
| PostgreSQL | datastore / dentro del prototipo | PostgreSQL | pipelines, incidents, diagnoses, human_reviews, recommendations, metrics, audit_metadata, evidence_references, traceability_metadata |
| Evidence and Artifact Storage | datastore / dentro del prototipo | Azure Blob Storage | large_logs, technical_evidence, pipeline_artifacts, diagnostic_reports, historical_logs_when_authorized |
| Technical Users | actor / externo al prototipo | No aplica | Querying and validation |
| Microsoft Entra ID | external_system / externo al prototipo | Microsoft Entra ID | corporate_authentication, identity_token_issuance |
| GitHub Actions | external_system / externo al prototipo | GitHub Actions | ci_cd_execution_and_evidence_source |

### Relaciones

| Nº | Origen → destino | Relación completa | Protocolo | Estilo |
|---|---|---|---|---|
| 01 | Pipeline Service → PostgreSQL | Persists pipelines, stages, states and execution metadata | PostgreSQL | sync |
| 02 | Log/Event Service → PostgreSQL | Persists and queries normalized evidence metadata and references | PostgreSQL | sync |
| 03 | Log/Event Service → Evidence and Artifact Storage | Stores and resolves references to large logs and evidence | Object Storage API | sync |
| 04 | Diagnostic & Recommendation Service → PostgreSQL | Persists diagnosis, recommendations and evidence links | PostgreSQL | sync |
| 05 | Technical Users → AIOps Web Dashboard | Queries results and records human review | HTTPS | sync |
| 06 | AIOps Web Dashboard → Microsoft Entra ID | Authenticates corporate users | OIDC/OAuth2/HTTPS | sync |
| 07 | AIOps Web Dashboard → Azure API Management | Consumes protected prototype APIs | REST/HTTPS | sync |
| 08 | Azure API Management → Pipeline Service | Routes pipeline and execution queries | REST/HTTPS | sync |
| 09 | Azure API Management → Log/Event Service | Routes log, event and evidence queries | REST/HTTPS | sync |
| 10 | Azure API Management → Diagnostic & Recommendation Service | Routes diagnosis and review queries and operations | REST/HTTPS | sync |
| 11 | Diagnostic & Recommendation Service → PostgreSQL | Persists human review decisions and traceability | PostgreSQL | sync |
| 12 | GitHub Actions → Azure API Management | Queries diagnostic_output to publish the workflow artifact | REST/HTTPS | sync |
