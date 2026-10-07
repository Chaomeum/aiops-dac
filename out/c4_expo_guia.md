# C4 de contenedores para diapositivas

Modelo de presentación: `model/c4_container_presentation.yml`. Arquitectura: `model/architecture.yml`.
Se conserva la proyección C4 canónica: todos sus nodos, fronteras, relaciones, protocolos y estilos.
PostgreSQL/pgvector conserva la agrupación de C4 2A; Human Review se proyecta en su contenedor padre.
Los nombres y tecnologías completos permanecen en las cajas. Las flechas usan números y una leyenda lateral.
SVG y PNG: 1920×1080, formato 16:9. Diseño propuesto, sin acreditar implementación.

## C4 Level 2A — Ingesta y Procesamiento AIOps

[SVG](c4_expo_2a.svg) · [PNG](c4_expo_2a.png)

Las fuentes externas entregan evidencia a ingesta, que la protege antes del topic de Service Bus. Tres suscripciones alimentan Pipeline, Log/Event y NLP. NLP entrega evidencia a correlación y esta al servicio diagnóstico, que orquesta RAG e inferencia con Azure OpenAI. PostgreSQL/pgvector y Blob conservan datos y evidencias. La causa probable requiere revisión humana.

### Contenedores, actores y sistemas externos

| Nombre exacto | Tipo / frontera | Tecnologías | Responsabilidades del modelo |
|---|---|---|---|
| Servicio de Ingesta y Normalización | container / dentro del prototipo | Azure Container Apps, Java / Spring Boot | authorized_capture, canonical_event_mapping, validation, parsing, cleaning, normalization, operational_noise_filtering, masking, anonymization, secret_filtering, data_minimization, correlation_id_assignment, evidence_metadata_capture |
| Azure Service Bus | container / dentro del prototipo | Azure Service Bus | persistent_asynchronous_messaging |
| Pipeline Service | container / dentro del prototipo | Azure Container Apps, Java / Spring Boot | register_pipeline, register_execution, maintain_pipeline_stages, maintain_execution_state, maintain_execution_metadata |
| Log/Event Service | container / dentro del prototipo | Azure Container Apps, Java / Spring Boot | register_normalized_evidence, query_logs_by_incident, query_events_by_incident, query_evidence_by_correlation_id, preserve_source_metadata, resolve_external_evidence_references |
| Procesamiento NLP de Logs | container / dentro del prototipo | Azure Container Apps, Python / FastAPI, Drain3 | semantic_representation, log_preprocessing, signal_preparation |
| Servicio de Correlación de Evidencias | container / dentro del prototipo | Azure Container Apps, Java / Spring Boot | Contexto del incidente |
| Diagnostic & Recommendation Service | container / dentro del prototipo | Azure Container Apps, Java / Spring Boot | generate_initial_recommendations, associate_recommendation_with_probable_cause, associate_recommendation_with_evidence, expose_evidence_limitations, orchestrate_diagnostic_flow |
| Recuperación de Conocimiento RAG | container / dentro del prototipo | Azure Container Apps, Python / FastAPI | retrieve_authorized_knowledge, semantic_search, preserve_provenance, interact_with_vector_store |
| PostgreSQL | datastore / dentro del prototipo | PostgreSQL / pgvector | pipelines, incidents, diagnoses, human_reviews, recommendations, metrics, audit_metadata, evidence_references, traceability_metadata |
| Almacenamiento de Evidencias y Artefactos | datastore / dentro del prototipo | Azure Blob Storage | large_logs, technical_evidence, pipeline_artifacts, diagnostic_reports, historical_logs_when_authorized |
| GitHub Actions | external_system / externo al prototipo | GitHub Actions | ci_cd_execution_and_evidence_source |
| Fuentes de Observabilidad y Runtime Compatibles | external_system / externo al prototipo | Azure Monitor, Application Insights | Telemetría autorizada |
| Azure OpenAI Service | external_system / externo al prototipo | Familia GPT-4 | Inferencia por API |

### Relaciones

| Nº | Origen → destino | Relación completa | Protocolo | Estilo |
|---|---|---|---|---|
| 01 | GitHub Actions → Servicio de Ingesta y Normalización | Emite eventos autorizados del workflow | HTTPS/Webhook | event |
| 02 | Azure Service Bus → Pipeline Service | Entrega eventos de ejecución para registrar contexto del pipeline | Azure Service Bus | async |
| 03 | Azure Service Bus → Log/Event Service | Entrega evidencia normalizada para registro y consulta | Azure Service Bus | async |
| 04 | Pipeline Service → PostgreSQL | Persiste pipelines, etapas, estados y metadatos de ejecución | PostgreSQL | sync |
| 05 | Log/Event Service → PostgreSQL | Persiste y consulta metadatos y referencias de evidencia normalizada | PostgreSQL | sync |
| 06 | Log/Event Service → Almacenamiento de Evidencias y Artefactos | Almacena y resuelve referencias de logs extensos y evidencias | Object Storage API | sync |
| 07 | Diagnostic & Recommendation Service → PostgreSQL | Persiste diagnóstico, recomendaciones y vínculos con evidencia | PostgreSQL | sync |
| 08 | Servicio de Ingesta y Normalización → GitHub Actions | Recupera logs, artefactos y metadatos autorizados | GitHub API/HTTPS | sync |
| 09 | Servicio de Ingesta y Normalización → Azure Service Bus | Publica evidencia normalizada y protegida | Azure Service Bus | async |
| 10 | Azure Service Bus → Procesamiento NLP de Logs | Entrega eventos normalizados para procesamiento | Azure Service Bus | async |
| 11 | Procesamiento NLP de Logs → Servicio de Correlación de Evidencias | Entrega logs y evidencia procesada para correlación | REST/HTTPS | sync |
| 12 | Servicio de Correlación de Evidencias → PostgreSQL | Registra contexto correlacionado y trazabilidad | PostgreSQL | sync |
| 13 | Recuperación de Conocimiento RAG → PostgreSQL | Recupera conocimiento operacional semánticamente relacionado | PostgreSQL/pgvector | sync |
| 14 | Fuentes de Observabilidad y Runtime Compatibles → Servicio de Ingesta y Normalización | Proporciona telemetría y evidencia operacional autorizada | REST/HTTPS | sync |
| 15 | Servicio de Correlación de Evidencias → Diagnostic & Recommendation Service | Entrega contexto correlacionado del incidente para diagnóstico asistido | REST/HTTPS | sync |
| 16 | Diagnostic & Recommendation Service → Recuperación de Conocimiento RAG | Solicita conocimiento contextual autorizado para el incidente | REST/HTTPS | sync |
| 17 | Diagnostic & Recommendation Service → Azure OpenAI Service | Solicita inferencia diagnóstica con evidencia saneada y contexto RAG | Azure OpenAI API/HTTPS | sync |
| 18 | Diagnostic & Recommendation Service → PostgreSQL | Persiste decisiones y trazabilidad de revisión humana | PostgreSQL | sync |

## C4 Level 2B — Consumo, Gobierno y Persistencia

[SVG](c4_expo_2b.svg) · [PNG](c4_expo_2b.png)

El usuario accede al dashboard, se autentica con Entra ID y consume APIs protegidas por APIM. Pipeline, Log/Event y diagnóstico conservan los datos y la revisión humana en PostgreSQL; Log/Event administra evidencias en Blob. GitHub Actions consulta el diagnóstico mediante APIM y publica su artifact. La revisión pertenece al servicio diagnóstico, sin otro microservicio.

### Contenedores, actores y sistemas externos

| Nombre exacto | Tipo / frontera | Tecnologías | Responsabilidades del modelo |
|---|---|---|---|
| Dashboard Web AIOps | container / dentro del prototipo | Azure Static Web Apps, TypeScript / React, SPA | incident_query, diagnosis_query, evidence_query, recommendation_query, pipeline_status_query, tmd_metrics, comparative_diagnosis_metrics, human_review_registration, human_review_status_display, distinguish_generated_hypothesis_from_validated_diagnosis, role_protected_access |
| Azure API Management | container / dentro del prototipo | Azure API Management | protected_api_entry_point, request_routing, access_policy_enforcement |
| Pipeline Service | container / dentro del prototipo | Azure Container Apps, Java / Spring Boot | register_pipeline, register_execution, maintain_pipeline_stages, maintain_execution_state, maintain_execution_metadata |
| Log/Event Service | container / dentro del prototipo | Azure Container Apps, Java / Spring Boot | register_normalized_evidence, query_logs_by_incident, query_events_by_incident, query_evidence_by_correlation_id, preserve_source_metadata, resolve_external_evidence_references |
| Diagnostic & Recommendation Service | container / dentro del prototipo | Azure Container Apps, Java / Spring Boot | generate_initial_recommendations, associate_recommendation_with_probable_cause, associate_recommendation_with_evidence, expose_evidence_limitations, orchestrate_diagnostic_flow |
| PostgreSQL | datastore / dentro del prototipo | PostgreSQL | pipelines, incidents, diagnoses, human_reviews, recommendations, metrics, audit_metadata, evidence_references, traceability_metadata |
| Almacenamiento de Evidencias y Artefactos | datastore / dentro del prototipo | Azure Blob Storage | large_logs, technical_evidence, pipeline_artifacts, diagnostic_reports, historical_logs_when_authorized |
| Usuarios Técnicos | actor / externo al prototipo | No aplica | Consulta y validación |
| Microsoft Entra ID | external_system / externo al prototipo | Microsoft Entra ID | corporate_authentication, identity_token_issuance |
| GitHub Actions | external_system / externo al prototipo | GitHub Actions | ci_cd_execution_and_evidence_source |

### Relaciones

| Nº | Origen → destino | Relación completa | Protocolo | Estilo |
|---|---|---|---|---|
| 01 | Pipeline Service → PostgreSQL | Persiste pipelines, etapas, estados y metadatos de ejecución | PostgreSQL | sync |
| 02 | Log/Event Service → PostgreSQL | Persiste y consulta metadatos y referencias de evidencia normalizada | PostgreSQL | sync |
| 03 | Log/Event Service → Almacenamiento de Evidencias y Artefactos | Almacena y resuelve referencias de logs extensos y evidencias | Object Storage API | sync |
| 04 | Diagnostic & Recommendation Service → PostgreSQL | Persiste diagnóstico, recomendaciones y vínculos con evidencia | PostgreSQL | sync |
| 05 | Usuarios Técnicos → Dashboard Web AIOps | Consulta resultados y registra revisión humana | HTTPS | sync |
| 06 | Dashboard Web AIOps → Microsoft Entra ID | Autentica usuarios corporativos | OIDC/OAuth2/HTTPS | sync |
| 07 | Dashboard Web AIOps → Azure API Management | Consume APIs protegidas del prototipo | REST/HTTPS | sync |
| 08 | Azure API Management → Pipeline Service | Enruta consultas de pipelines y ejecuciones | REST/HTTPS | sync |
| 09 | Azure API Management → Log/Event Service | Enruta consultas de logs, eventos y evidencias | REST/HTTPS | sync |
| 10 | Azure API Management → Diagnostic & Recommendation Service | Enruta consultas y operaciones de diagnóstico y revisión | REST/HTTPS | sync |
| 11 | Diagnostic & Recommendation Service → PostgreSQL | Persiste decisiones y trazabilidad de revisión humana | PostgreSQL | sync |
| 12 | GitHub Actions → Azure API Management | Consulta diagnostic_output para publicar el artifact del workflow | REST/HTTPS | sync |
