<!-- GENERATED — DO NOT EDIT. SSOT: model/domain.yml -->
# Diccionario de datos

Modelo: `1.0.0`. Una instancia PostgreSQL; 17 tablas.

Los tipos enum se materializan en el schema propietario de cada tabla.
FK significa constraint físico intra-schema; logical_ref significa ID sin FK física.

## Schema `ops`

Operación de workflows e incidentes.

Owners permitidos: pipeline_service.

### `ops.repositories`

Repositorio GitHub autorizado; entidad distinta del workflow monitorizado.

Owner: `pipeline_service`. scope_basis: `approved_domain`. status: `confirmed`.

Fuentes: SRC_CHARTER#Alcance-del-Proyecto, architecture.yml#github, DD-001.

| Columna | Tipo | PK | FK | logical_ref | Nullable | Unique | Enum | Descripción | Fuente | Assumption |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| id | uuid | Sí | — | — | No | No | — | Identificador estable asignado por el servicio propietario. | SRC_CHARTER#Alcance-del-Proyecto; architecture.yml#github; DD-001 | A-001 |
| github_repository_id | text | No | — | — | No | Sí | — | ID externo del repositorio GitHub. | SRC_CHARTER#Alcance-del-Proyecto; architecture.yml#github; DD-001 | A-003 |
| full_name | text | No | — | — | No | No | — | Nombre owner/repository para presentación. | SRC_CHARTER#Alcance-del-Proyecto; architecture.yml#github; DD-001 | — |
| default_branch | text | No | — | — | Sí | No | — | Rama por defecto suministrada por GitHub. | SRC_CHARTER#Alcance-del-Proyecto; architecture.yml#github; DD-001 | — |
| created_at | timestamptz | No | — | — | No | No | — | Instante de persistencia; permite aplicar retención cuando corresponde. | SRC_ADR_013; DD-015 | A-002 |

### `ops.pipelines`

Pipeline equivale directamente a un GitHub Actions workflow monitorizado.

Owner: `pipeline_service`. scope_basis: `approved_domain`. status: `confirmed`.

Fuentes: SRC_ADR_018, architecture.yml#pipeline_service, docs/research/arquitectura-informacion.md, DD-001.

Claves únicas compuestas: `(repository_id, github_workflow_id)`.

| Columna | Tipo | PK | FK | logical_ref | Nullable | Unique | Enum | Descripción | Fuente | Assumption |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| id | uuid | Sí | — | — | No | No | — | Identificador estable asignado por el servicio propietario. | SRC_ADR_018; architecture.yml#pipeline_service; docs/research/arquitectura-informacion.md; DD-001 | A-001 |
| repository_id | uuid | No | ops.repositories.id | — | No | Compuesto: (repository_id, github_workflow_id) | — | Repositorio del workflow. | SRC_ADR_018; architecture.yml#pipeline_service; docs/research/arquitectura-informacion.md; DD-001 | — |
| github_workflow_id | text | No | — | — | No | Compuesto: (repository_id, github_workflow_id) | — | ID externo del workflow, único dentro de su repositorio. | SRC_ADR_018; architecture.yml#pipeline_service; docs/research/arquitectura-informacion.md; DD-001 | A-003 |
| workflow_name | text | No | — | — | No | No | — | Nombre del workflow monitorizado. | SRC_ADR_018; architecture.yml#pipeline_service; docs/research/arquitectura-informacion.md; DD-001 | — |
| workflow_file | text | No | — | — | No | No | — | Ruta declarada del workflow. | SRC_ADR_018; architecture.yml#pipeline_service; docs/research/arquitectura-informacion.md; DD-001 | — |
| environment | text | No | — | — | Sí | No | — | Entorno operacional suministrado por configuración autorizada. | SRC_ADR_018; architecture.yml#pipeline_service; docs/research/arquitectura-informacion.md; DD-001 | — |
| criticality | ops.PipelineCriticality | No | — | — | No | No | PipelineCriticality | Criticidad del pipeline; distinta de la severidad del incidente. | docs/research/arquitectura-informacion.md | — |
| monitoring_status | ops.MonitoringStatus | No | — | — | No | No | MonitoringStatus | Estado de monitorización. | docs/research/arquitectura-informacion.md | — |
| responsible_team_ref | text | No | — | — | Sí | No | — | Referencia externa al equipo responsable; sin tabla teams. | docs/research/arquitectura-informacion.md | — |
| responsible_team_name_snapshot | text | No | — | — | Sí | No | — | Nombre del equipo al registrar configuración. | docs/research/arquitectura-informacion.md | — |
| created_at | timestamptz | No | — | — | No | No | — | Instante de persistencia; permite aplicar retención cuando corresponde. | SRC_ADR_013; DD-015 | A-002 |

### `ops.pipeline_executions`

Ejecución de un workflow; conserva contexto GitHub Actions y resultado de fallo autorizado.

Owner: `pipeline_service`. scope_basis: `approved_domain`. status: `confirmed`.

Fuentes: architecture.yml#pipeline_service, SRC_ADR_010, DD-002.

Claves únicas compuestas: `(pipeline_id, github_run_id, run_attempt)`.

Checks: `run_attempt > 0`.

| Columna | Tipo | PK | FK | logical_ref | Nullable | Unique | Enum | Descripción | Fuente | Assumption |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| id | uuid | Sí | — | — | No | No | — | Identificador estable asignado por el servicio propietario. | architecture.yml#pipeline_service; SRC_ADR_010; DD-002 | A-001 |
| pipeline_id | uuid | No | ops.pipelines.id | — | No | Compuesto: (pipeline_id, github_run_id, run_attempt) | — | Pipeline que fue ejecutado. | architecture.yml#pipeline_service; SRC_ADR_010; DD-002 | — |
| github_run_id | text | No | — | — | No | Compuesto: (pipeline_id, github_run_id, run_attempt) | — | ID externo del run. | architecture.yml#pipeline_service; SRC_ADR_010; DD-002 | A-003 |
| run_attempt | integer | No | — | — | No | Compuesto: (pipeline_id, github_run_id, run_attempt) | — | Intento del run; distingue reejecuciones del mismo ID externo. | architecture.yml#pipeline_service; SRC_ADR_010; DD-002 | A-003 |
| branch | text | No | — | — | No | No | — | Rama ejecutada. | architecture.yml#pipeline_service; SRC_ADR_010; DD-002 | — |
| commit_sha | text | No | — | — | No | No | — | Referencia al commit ejecutado. | architecture.yml#pipeline_service; SRC_ADR_010; DD-002 | — |
| external_status | text | No | — | — | No | No | — | Estado del run suministrado por GitHub; no define un enum interno nuevo. | architecture.yml#pipeline_service; SRC_ADR_010; DD-002 | — |
| external_conclusion | text | No | — | — | Sí | No | — | Conclusión externa cuando está disponible. | architecture.yml#pipeline_service; SRC_ADR_010; DD-002 | — |
| failed | boolean | No | — | — | No | No | — | Indica un fallo identificado por GitHub Actions; no representa detección AIOps. | architecture.yml#pipeline_service; SRC_ADR_010; DD-002 | A-004 |
| started_at | timestamptz | No | — | — | Sí | No | — | Inicio de ejecución. | architecture.yml#pipeline_service; SRC_ADR_010; DD-002 | A-002 |
| completed_at | timestamptz | No | — | — | Sí | No | — | Fin de ejecución. | architecture.yml#pipeline_service; SRC_ADR_010; DD-002 | A-002 |
| correlation_id | text | No | — | — | No | No | — | Identificador de correlación end-to-end; no contiene información sensible. | architecture.yml#CTRL-003 | — |
| created_at | timestamptz | No | — | — | No | No | — | Instante de persistencia; permite aplicar retención cuando corresponde. | SRC_ADR_013; DD-015 | A-002 |

### `ops.execution_stages`

Etapas de una ejecución; los jobs pueden suministrar evidencia sin tablas adicionales.

Owner: `pipeline_service`. scope_basis: `approved_domain`. status: `confirmed`.

Fuentes: architecture.yml#pipeline_service, docs/research/arquitectura-informacion.md, DD-013.

Claves únicas compuestas: `(execution_id, stage)`.

| Columna | Tipo | PK | FK | logical_ref | Nullable | Unique | Enum | Descripción | Fuente | Assumption |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| id | uuid | Sí | — | — | No | No | — | Identificador estable asignado por el servicio propietario. | architecture.yml#pipeline_service; docs/research/arquitectura-informacion.md; DD-013 | A-001 |
| execution_id | uuid | No | ops.pipeline_executions.id | — | No | Compuesto: (execution_id, stage) | — | Ejecución a la que pertenece la etapa. | architecture.yml#pipeline_service; docs/research/arquitectura-informacion.md; DD-013 | — |
| stage | ops.PipelineStage | No | — | — | No | Compuesto: (execution_id, stage) | PipelineStage | Etapa operacional normalizada; no es nivel de log. | architecture.yml#pipeline_service; docs/research/arquitectura-informacion.md; DD-013 | — |
| external_status | text | No | — | — | Sí | No | — | Estado de etapa suministrado por evidencia autorizada. | architecture.yml#pipeline_service; docs/research/arquitectura-informacion.md; DD-013 | — |
| started_at | timestamptz | No | — | — | Sí | No | — | Inicio observado de la etapa. | architecture.yml#pipeline_service; docs/research/arquitectura-informacion.md; DD-013 | A-002 |
| completed_at | timestamptz | No | — | — | Sí | No | — | Fin observado de la etapa. | architecture.yml#pipeline_service; docs/research/arquitectura-informacion.md; DD-013 | A-002 |
| correlation_id | text | No | — | — | No | No | — | Identificador de correlación end-to-end; no contiene información sensible. | architecture.yml#CTRL-003 | — |
| created_at | timestamptz | No | — | — | No | No | — | Instante de persistencia; permite aplicar retención cuando corresponde. | SRC_ADR_013; DD-015 | A-002 |

### `ops.incidents`

Incidente originado en una ejecución fallida, con asignación y tiempos operacionales.

Owner: `pipeline_service`. scope_basis: `approved_domain`. status: `confirmed`.

Fuentes: SRC_ADR_018, architecture.yml#INV-007, docs/research/arquitectura-informacion.md, DD-002.

Constraints complementarias: exactly_one_failed_origin, origin_pipeline_consistency.

| Columna | Tipo | PK | FK | logical_ref | Nullable | Unique | Enum | Descripción | Fuente | Assumption |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| id | uuid | Sí | — | — | No | No | — | Identificador estable asignado por el servicio propietario. | SRC_ADR_018; architecture.yml#INV-007; docs/research/arquitectura-informacion.md; DD-002 | A-001 |
| pipeline_id | uuid | No | ops.pipelines.id | — | No | No | — | Pipeline del incidente; debe coincidir con el de su ORIGIN. | SRC_ADR_018; architecture.yml#INV-007; docs/research/arquitectura-informacion.md; DD-002 | — |
| status | ops.IncidentStatus | No | — | — | No | No | IncidentStatus | Estado operacional del incidente. | SRC_ADR_018; architecture.yml#INV-007; docs/research/arquitectura-informacion.md; DD-002 | — |
| severity | ops.Severity | No | — | — | Sí | No | Severity | Severidad operacional; nullable hasta disponer de regla aprobada de derivación. | SRC_ADR_018; architecture.yml#INV-007; docs/research/arquitectura-informacion.md; DD-002 | A-005 |
| stage | ops.PipelineStage | No | — | — | No | No | PipelineStage | Etapa del fallo. | SRC_ADR_018; architecture.yml#INV-007; docs/research/arquitectura-informacion.md; DD-002 | — |
| summary | text | No | — | — | No | No | — | Resumen saneado del fallo observado. | SRC_ADR_018; architecture.yml#INV-007; docs/research/arquitectura-informacion.md; DD-002 | — |
| assignee_ref | text | No | — | — | Sí | No | — | Referencia externa a identidad corporativa Entra ID; distinta de ownership del pipeline. | SRC_ADR_018; architecture.yml#INV-007; docs/research/arquitectura-informacion.md; DD-002 | — |
| assignee_display_name_snapshot | text | No | — | — | Sí | No | — | Nombre del assignee al asignar; no es maestro de identidad. | SRC_ADR_018; architecture.yml#INV-007; docs/research/arquitectura-informacion.md; DD-002 | — |
| detected_at | timestamptz | No | — | — | No | No | — | Instante de detección del fallo; origen del cálculo TMD. | SRC_ADR_018; architecture.yml#INV-007; docs/research/arquitectura-informacion.md; DD-002 | A-002 |
| remediation_started_at | timestamptz | No | — | — | Sí | No | — | Start remediation registra estado y tiempo; no ejecuta correcciones. | SRC_ADR_018; architecture.yml#INV-007; docs/research/arquitectura-informacion.md; DD-002 | A-002 |
| verification_started_at | timestamptz | No | — | — | Sí | No | — | Inicio de verificación bajo control humano. | SRC_ADR_018; architecture.yml#INV-007; docs/research/arquitectura-informacion.md; DD-002 | A-002 |
| resolved_at | timestamptz | No | — | — | Sí | No | — | Resolución operacional del incidente. | SRC_ADR_018; architecture.yml#INV-007; docs/research/arquitectura-informacion.md; DD-002 | A-002 |
| correlation_id | text | No | — | — | No | No | — | Identificador de correlación end-to-end; no contiene información sensible. | architecture.yml#CTRL-003 | — |
| created_at | timestamptz | No | — | — | No | No | — | Instante de persistencia; permite aplicar retención cuando corresponde. | SRC_ADR_013; DD-015 | A-002 |

### `ops.incident_runs`

Vincula un incidente con exactamente un ORIGIN fallido y cero o más VERIFICATION.

Owner: `pipeline_service`. scope_basis: `approved_domain`. status: `confirmed`.

Fuentes: SRC_ADR_018, model/domain_decisions.md, DD-002.

Claves únicas compuestas: `(incident_id, execution_id)`.

Constraints complementarias: at_most_one_origin.

| Columna | Tipo | PK | FK | logical_ref | Nullable | Unique | Enum | Descripción | Fuente | Assumption |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| id | uuid | Sí | — | — | No | No | — | Identificador estable asignado por el servicio propietario. | SRC_ADR_018; model/domain_decisions.md; DD-002 | A-001 |
| incident_id | uuid | No | ops.incidents.id | — | No | Compuesto: (incident_id, execution_id) | — | Incidente propietario de la relación. | SRC_ADR_018; model/domain_decisions.md; DD-002 | — |
| execution_id | uuid | No | ops.pipeline_executions.id | — | No | Compuesto: (incident_id, execution_id) | — | Ejecución ORIGIN o VERIFICATION; no fija política adicional del workflow de verificación. | SRC_ADR_018; model/domain_decisions.md; DD-002 | — |
| role | ops.IncidentRunRole | No | — | — | No | No | IncidentRunRole | Rol del run en el incidente. | SRC_ADR_018; model/domain_decisions.md; DD-002 | — |
| correlation_id | text | No | — | — | No | No | — | Identificador de correlación end-to-end; no contiene información sensible. | architecture.yml#CTRL-003 | — |
| created_at | timestamptz | No | — | — | No | No | — | Instante de persistencia; permite aplicar retención cuando corresponde. | SRC_ADR_013; DD-015 | A-002 |

### `ops.pipeline_access_grants`

Representación provisional de capacidades por pipeline; no requisito core ni implementación definitiva RBAC.

Owner: `pipeline_service`. scope_basis: `ia_only`. status: `inferred`.

Fuentes: docs/research/arquitectura-informacion.md, SRC_ADR_003, DD-017.

Claves únicas compuestas: `(pipeline_id, principal_ref, capability)`.

| Columna | Tipo | PK | FK | logical_ref | Nullable | Unique | Enum | Descripción | Fuente | Assumption |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| id | uuid | Sí | — | — | No | No | — | Identificador estable asignado por el servicio propietario. | docs/research/arquitectura-informacion.md; SRC_ADR_003; DD-017 | A-001 |
| pipeline_id | uuid | No | ops.pipelines.id | — | No | Compuesto: (pipeline_id, principal_ref, capability) | — | Pipeline al que corresponde la capacidad. | docs/research/arquitectura-informacion.md; SRC_ADR_003; DD-017 | — |
| principal_ref | text | No | — | — | No | Compuesto: (pipeline_id, principal_ref, capability) | — | Referencia controlada a principal corporativo Entra ID; sin tabla users/roles. | docs/research/arquitectura-informacion.md; SRC_ADR_003; DD-017 | — |
| capability | ops.AccessCapability | No | — | — | No | Compuesto: (pipeline_id, principal_ref, capability) | AccessCapability | Capacidad funcional propuesta por arquitectura de información. | docs/research/arquitectura-informacion.md; SRC_ADR_003; DD-017 | — |
| correlation_id | text | No | — | — | No | No | — | Identificador de correlación end-to-end; no contiene información sensible. | architecture.yml#CTRL-003 | — |
| created_at | timestamptz | No | — | — | No | No | — | Instante de persistencia; permite aplicar retención cuando corresponde. | SRC_ADR_013; DD-015 | A-002 |

## Schema `evidence`

Evidencia normalizada y contexto; ownership por tabla.

Owners permitidos: log_event_service, evidence_correlation_engine.

### `evidence.evidence_items`

Metadata y extracto normalizado; logs grandes en Azure Blob Storage por referencia sin SAS ni secretos.

Owner: `log_event_service`. scope_basis: `approved_domain`. status: `confirmed`.

Fuentes: architecture.yml#log_event_service, architecture.yml#object_evidence_store, architecture.yml#INV-001, SRC_ADR_013, DD-006.

Retención: 365 días (ADR-013), anclada en `created_at`; no hay purge jobs.

Checks: `size_bytes IS NULL OR size_bytes >= 0`; `(storage_container IS NULL) = (blob_object_key IS NULL)`.

| Columna | Tipo | PK | FK | logical_ref | Nullable | Unique | Enum | Descripción | Fuente | Assumption |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| id | uuid | Sí | — | — | No | No | — | Identificador estable asignado por el servicio propietario. | architecture.yml#log_event_service; architecture.yml#object_evidence_store; architecture.yml#INV-001; SRC_ADR_013; DD-006 | A-001 |
| incident_id | uuid | No | — | ops.incidents.id | No | No | — | Incidente asociado por ID lógico. | architecture.yml#log_event_service; architecture.yml#object_evidence_store; architecture.yml#INV-001; SRC_ADR_013; DD-006 | — |
| execution_id | uuid | No | — | ops.pipeline_executions.id | No | No | — | Ejecución observada por ID lógico. | architecture.yml#log_event_service; architecture.yml#object_evidence_store; architecture.yml#INV-001; SRC_ADR_013; DD-006 | — |
| correlation_id | text | No | — | — | No | No | — | Identificador de correlación end-to-end; no contiene información sensible. | architecture.yml#CTRL-003 | — |
| source | text | No | — | — | No | No | — | Procedencia operacional autorizada, independiente de provenance RAG. | architecture.yml#log_event_service; architecture.yml#object_evidence_store; architecture.yml#INV-001; SRC_ADR_013; DD-006 | — |
| stage | evidence.PipelineStage | No | — | — | No | No | PipelineStage | Etapa operacional observada. | architecture.yml#log_event_service; architecture.yml#object_evidence_store; architecture.yml#INV-001; SRC_ADR_013; DD-006 | — |
| job | text | No | — | — | Sí | No | — | Job externo cuando existe. | architecture.yml#log_event_service; architecture.yml#object_evidence_store; architecture.yml#INV-001; SRC_ADR_013; DD-006 | — |
| summary | text | No | — | — | No | No | — | Resumen normalizado y saneado. | architecture.yml#log_event_service; architecture.yml#object_evidence_store; architecture.yml#INV-001; SRC_ADR_013; DD-006 | — |
| excerpt | text | No | — | — | Sí | No | — | Extracto minimizado y enmascarado; nunca payload sensible crudo. | architecture.yml#log_event_service; architecture.yml#object_evidence_store; architecture.yml#INV-001; SRC_ADR_013; DD-006 | — |
| observed_at | timestamptz | No | — | — | No | No | — | Instante observado en la fuente. | architecture.yml#log_event_service; architecture.yml#object_evidence_store; architecture.yml#INV-001; SRC_ADR_013; DD-006 | A-002 |
| sequence | bigint | No | — | — | Sí | No | — | Orden de evidencia cuando la fuente lo proporciona. | architecture.yml#log_event_service; architecture.yml#object_evidence_store; architecture.yml#INV-001; SRC_ADR_013; DD-006 | — |
| storage_container | text | No | — | — | Sí | No | — | Nombre de container Blob; sin tokens, credenciales ni URL SAS. | architecture.yml#log_event_service; architecture.yml#object_evidence_store; architecture.yml#INV-001; SRC_ADR_013; DD-006 | — |
| blob_object_key | text | No | — | — | Sí | No | — | Clave del objeto Blob; sin SAS ni material secreto. | architecture.yml#log_event_service; architecture.yml#object_evidence_store; architecture.yml#INV-001; SRC_ADR_013; DD-006 | — |
| content_hash | text | No | — | — | Sí | No | — | Hash del objeto cuando existe; algoritmo no fijado. | architecture.yml#log_event_service; architecture.yml#object_evidence_store; architecture.yml#INV-001; SRC_ADR_013; DD-006 | — |
| size_bytes | bigint | No | — | — | Sí | No | — | Tamaño externo en bytes cuando está disponible. | architecture.yml#log_event_service; architecture.yml#object_evidence_store; architecture.yml#INV-001; SRC_ADR_013; DD-006 | — |
| created_at | timestamptz | No | — | — | No | No | — | Instante de persistencia; permite aplicar retención cuando corresponde. | SRC_ADR_013; DD-015 | A-002 |

### `evidence.correlated_contexts`

Snapshot saneado del contexto correlacionado; conserva los IDs de evidencia utilizados.

Owner: `evidence_correlation_engine`. scope_basis: `approved_domain`. status: `confirmed`.

Fuentes: architecture.yml#evidence_correlation_engine, SRC_ADR_015, DD-014.

Retención: 365 días (ADR-013), anclada en `created_at`; no hay purge jobs.

| Columna | Tipo | PK | FK | logical_ref | Nullable | Unique | Enum | Descripción | Fuente | Assumption |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| id | uuid | Sí | — | — | No | No | — | Identificador estable asignado por el servicio propietario. | architecture.yml#evidence_correlation_engine; SRC_ADR_015; DD-014 | A-001 |
| incident_id | uuid | No | — | ops.incidents.id | No | No | — | Incidente del contexto. | architecture.yml#evidence_correlation_engine; SRC_ADR_015; DD-014 | — |
| execution_id | uuid | No | — | ops.pipeline_executions.id | No | No | — | Ejecución correlacionada; no fusionar ejecuciones no relacionadas. | architecture.yml#evidence_correlation_engine; SRC_ADR_015; DD-014 | — |
| evidence_ids | uuid[] | No | — | evidence.evidence_items.id | No | No | — | Colección de IDs lógicos de evidencia; otro servicio no modifica evidence_items. | architecture.yml#evidence_correlation_engine; SRC_ADR_015; DD-014 | A-006 |
| summary | text | No | — | — | No | No | — | Síntesis saneada del contexto operacional. | architecture.yml#evidence_correlation_engine; SRC_ADR_015; DD-014 | — |
| correlation_id | text | No | — | — | No | No | — | Identificador de correlación end-to-end; no contiene información sensible. | architecture.yml#CTRL-003 | — |
| created_at | timestamptz | No | — | — | No | No | — | Instante de persistencia; permite aplicar retención cuando corresponde. | SRC_ADR_013; DD-015 | A-002 |

## Schema `diagnosis`

Diagnósticos, recomendaciones y revisión.

Owners permitidos: recommendation_service.

### `diagnosis.diagnoses`

Snapshot diagnóstico versionado append-only; actual = versión mayor por incidente.

Owner: `recommendation_service`. scope_basis: `approved_domain`. status: `confirmed`.

Fuentes: architecture.yml#recommendation_service, architecture.yml#INV-005, SRC_ADR_013, DD-003.

Retención: 365 días (ADR-013), anclada en `created_at`; no hay purge jobs.

Claves únicas compuestas: `(incident_id, version)`.

Checks: `version > 0`; `status <> 'DIAGNOSIS_READY' OR (probable_cause IS NOT NULL AND btrim(probable_cause) <> '' AND diagnosis_ready_at IS NOT NULL)`.

Constraints complementarias: append_only.

| Columna | Tipo | PK | FK | logical_ref | Nullable | Unique | Enum | Descripción | Fuente | Assumption |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| id | uuid | Sí | — | — | No | No | — | Identificador estable asignado por el servicio propietario. | architecture.yml#recommendation_service; architecture.yml#INV-005; SRC_ADR_013; DD-003 | A-001 |
| incident_id | uuid | No | — | ops.incidents.id | No | Compuesto: (incident_id, version) | — | Incidente por referencia lógica; sin asociación JPA cross-context. | architecture.yml#recommendation_service; architecture.yml#INV-005; SRC_ADR_013; DD-003 | — |
| version | integer | No | — | — | No | Compuesto: (incident_id, version) | — | Versión positiva, única por incidente; cada nuevo snapshot se inserta. | architecture.yml#recommendation_service; architecture.yml#INV-005; SRC_ADR_013; DD-003 | — |
| status | diagnosis.DiagnosisStatus | No | — | — | No | No | DiagnosisStatus | Estado diagnóstico del snapshot. | architecture.yml#recommendation_service; architecture.yml#INV-005; SRC_ADR_013; DD-003 | — |
| probable_cause | text | No | — | — | Sí | No | — | Hipótesis de causa probable; obligatoria cuando DIAGNOSIS_READY. | architecture.yml#recommendation_service; architecture.yml#INV-005; SRC_ADR_013; DD-003 | A-007 |
| explanation | text | No | — | — | Sí | No | — | Explicación saneada del diagnóstico. | architecture.yml#recommendation_service; architecture.yml#INV-005; SRC_ADR_013; DD-003 | — |
| limitations | text | No | — | — | Sí | No | — | Limitaciones de evidencia/inferencia. | architecture.yml#recommendation_service; architecture.yml#INV-005; SRC_ADR_013; DD-003 | — |
| confidence | jsonb | No | — | — | Sí | No | — | Valor informado por el proveedor, sin imponer tipo numérico, escala ni rango. | architecture.yml#recommendation_service; architecture.yml#INV-005; SRC_ADR_013; DD-003 | A-008 |
| diagnosis_ready_at | timestamptz | No | — | — | Sí | No | — | Instante de disponibilidad de esta versión; TMD se calcula con detected_at del incidente. | architecture.yml#recommendation_service; architecture.yml#INV-005; SRC_ADR_013; DD-003 | A-002 |
| correlation_id | text | No | — | — | No | No | — | Identificador de correlación end-to-end; no contiene información sensible. | architecture.yml#CTRL-003 | — |
| created_at | timestamptz | No | — | — | No | No | — | Instante de persistencia; permite aplicar retención cuando corresponde. | SRC_ADR_013; DD-015 | A-002 |

### `diagnosis.recommendations`

Recomendación como entidad propia de una versión diagnóstica; no ejecuta remediación.

Owner: `recommendation_service`. scope_basis: `approved_domain`. status: `confirmed`.

Fuentes: architecture.yml#recommendation_service, SRC_ADR_016, SRC_ADR_013, DD-004.

Retención: 365 días (ADR-013), anclada en `created_at`; no hay purge jobs.

| Columna | Tipo | PK | FK | logical_ref | Nullable | Unique | Enum | Descripción | Fuente | Assumption |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| id | uuid | Sí | — | — | No | No | — | Identificador estable asignado por el servicio propietario. | architecture.yml#recommendation_service; SRC_ADR_016; SRC_ADR_013; DD-004 | A-001 |
| diagnosis_id | uuid | No | diagnosis.diagnoses.id | — | No | No | — | Versión que propone la recomendación. | architecture.yml#recommendation_service; SRC_ADR_016; SRC_ADR_013; DD-004 | — |
| description | text | No | — | — | No | No | — | Procedimiento o acción recomendada para evaluación humana. | architecture.yml#recommendation_service; SRC_ADR_016; SRC_ADR_013; DD-004 | — |
| critical | boolean | No | — | — | No | No | — | Marcado de recomendación crítica para gobierno humano. | architecture.yml#human_review_component | — |
| correlation_id | text | No | — | — | No | No | — | Identificador de correlación end-to-end; no contiene información sensible. | architecture.yml#CTRL-003 | — |
| created_at | timestamptz | No | — | — | No | No | — | Instante de persistencia; permite aplicar retención cuando corresponde. | SRC_ADR_013; DD-015 | A-002 |

### `diagnosis.diagnosis_evidence_links`

Traza qué evidencia operacional sustenta una versión diagnóstica.

Owner: `recommendation_service`. scope_basis: `approved_domain`. status: `confirmed`.

Fuentes: architecture.yml#diagnostic_output_component, SRC_ADR_013, DD-006.

Retención: 365 días (ADR-013), anclada en `created_at`; no hay purge jobs.

Claves únicas compuestas: `(diagnosis_id, evidence_id)`.

| Columna | Tipo | PK | FK | logical_ref | Nullable | Unique | Enum | Descripción | Fuente | Assumption |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| id | uuid | Sí | — | — | No | No | — | Identificador estable asignado por el servicio propietario. | architecture.yml#diagnostic_output_component; SRC_ADR_013; DD-006 | A-001 |
| diagnosis_id | uuid | No | diagnosis.diagnoses.id | — | No | Compuesto: (diagnosis_id, evidence_id) | — | Versión diagnóstica sustentada. | architecture.yml#diagnostic_output_component; SRC_ADR_013; DD-006 | — |
| evidence_id | uuid | No | — | evidence.evidence_items.id | No | Compuesto: (diagnosis_id, evidence_id) | — | Evidencia operacional consultada por ID lógico. | architecture.yml#diagnostic_output_component; SRC_ADR_013; DD-006 | — |
| correlation_id | text | No | — | — | No | No | — | Identificador de correlación end-to-end; no contiene información sensible. | architecture.yml#CTRL-003 | — |
| created_at | timestamptz | No | — | — | No | No | — | Instante de persistencia; permite aplicar retención cuando corresponde. | SRC_ADR_013; DD-015 | A-002 |

### `diagnosis.diagnosis_source_links`

Traza consulted_sources: Diagnosis → KnowledgeChunk → KnowledgeDocument.

Owner: `recommendation_service`. scope_basis: `approved_domain`. status: `confirmed`.

Fuentes: architecture.yml#diagnostic_output_component, architecture.yml#rag_retrieval, SRC_ADR_013, DD-007.

Retención: 365 días (ADR-013), anclada en `created_at`; no hay purge jobs.

Claves únicas compuestas: `(diagnosis_id, knowledge_chunk_id)`.

| Columna | Tipo | PK | FK | logical_ref | Nullable | Unique | Enum | Descripción | Fuente | Assumption |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| id | uuid | Sí | — | — | No | No | — | Identificador estable asignado por el servicio propietario. | architecture.yml#diagnostic_output_component; architecture.yml#rag_retrieval; SRC_ADR_013; DD-007 | A-001 |
| diagnosis_id | uuid | No | diagnosis.diagnoses.id | — | No | Compuesto: (diagnosis_id, knowledge_chunk_id) | — | Versión diagnóstica que consultó RAG. | architecture.yml#diagnostic_output_component; architecture.yml#rag_retrieval; SRC_ADR_013; DD-007 | — |
| knowledge_chunk_id | uuid | No | — | knowledge.knowledge_chunks.id | No | Compuesto: (diagnosis_id, knowledge_chunk_id) | — | Chunk consultado; documento reconstruible mediante FK de knowledge_chunks. | architecture.yml#diagnostic_output_component; architecture.yml#rag_retrieval; SRC_ADR_013; DD-007 | — |
| correlation_id | text | No | — | — | No | No | — | Identificador de correlación end-to-end; no contiene información sensible. | architecture.yml#CTRL-003 | — |
| created_at | timestamptz | No | — | — | No | No | — | Instante de persistencia; permite aplicar retención cuando corresponde. | SRC_ADR_013; DD-015 | A-002 |

### `diagnosis.human_reviews`

Revisión humana: ausencia = PENDING derivado; decision solo CONFIRMED, CORRECTED o REJECTED.

Owner: `recommendation_service`. scope_basis: `approved_domain`. status: `confirmed`.

Fuentes: SRC_ADR_011, SRC_ADR_016, architecture.yml#INV-006, SRC_ADR_013, DD-005.

Retención: 365 días (ADR-013), anclada en `created_at`; no hay purge jobs.

Checks: `decision <> 'CORRECTED' OR (actual_cause IS NOT NULL AND btrim(actual_cause) <> '')`.

| Columna | Tipo | PK | FK | logical_ref | Nullable | Unique | Enum | Descripción | Fuente | Assumption |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| id | uuid | Sí | — | — | No | No | — | Identificador estable asignado por el servicio propietario. | SRC_ADR_011; SRC_ADR_016; architecture.yml#INV-006; SRC_ADR_013; DD-005 | A-001 |
| diagnostic_id | uuid | No | diagnosis.diagnoses.id | — | No | No | — | Versión revisada; conserva el nombre contractual diagnostic_id de ADR-011. | SRC_ADR_011; SRC_ADR_016; architecture.yml#INV-006; SRC_ADR_013; DD-005 | — |
| reviewer_ref | text | No | — | — | No | No | — | Identidad externa del revisor corporativo; mapea reviewer del contrato. | SRC_ADR_011; SRC_ADR_016; architecture.yml#INV-006; SRC_ADR_013; DD-005 | — |
| decision | diagnosis.HumanReviewDecision | No | — | — | No | No | HumanReviewDecision | CONFIRMED acepta; CORRECTED aporta causa corregida; REJECTED rechaza sin alternativa validada. | SRC_ADR_011; SRC_ADR_016; architecture.yml#INV-006; SRC_ADR_013; DD-005 | — |
| timestamp | timestamptz | No | — | — | No | No | — | Instante de revisión del contrato. | SRC_ADR_011; SRC_ADR_016; architecture.yml#INV-006; SRC_ADR_013; DD-005 | A-002 |
| correlation_id | text | No | — | — | No | No | — | Identificador de correlación end-to-end; no contiene información sensible. | architecture.yml#CTRL-003 | — |
| actual_cause | text | No | — | — | Sí | No | — | Causa corregida suministrada por el revisor; requerida semánticamente en CORRECTED. | SRC_ADR_011; SRC_ADR_016; architecture.yml#INV-006; SRC_ADR_013; DD-005 | — |
| comment | text | No | — | — | Sí | No | — | Comentario saneado del revisor. | SRC_ADR_011; SRC_ADR_016; architecture.yml#INV-006; SRC_ADR_013; DD-005 | — |
| created_at | timestamptz | No | — | — | No | No | — | Instante de persistencia; permite aplicar retención cuando corresponde. | SRC_ADR_013; DD-015 | A-002 |

## Schema `knowledge`

Corpus autorizado recuperable.

Owners permitidos: rag_retrieval.

### `knowledge.knowledge_documents`

Corpus autorizado; prohíbe casos de evaluación y soluciones de referencia conforme a INV-010.

Owner: `rag_retrieval`. scope_basis: `approved_domain`. status: `confirmed`.

Fuentes: architecture.yml#rag_retrieval, architecture.yml#INV-010, SRC_ADR_007, DD-007.

Checks: `btrim(provenance) <> ''`; `corpus_kind <> 'reviewed_incidents' OR reviewed_incident_id IS NOT NULL`.

| Columna | Tipo | PK | FK | logical_ref | Nullable | Unique | Enum | Descripción | Fuente | Assumption |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| id | uuid | Sí | — | — | No | No | — | Identificador estable asignado por el servicio propietario. | architecture.yml#rag_retrieval; architecture.yml#INV-010; SRC_ADR_007; DD-007 | A-001 |
| corpus_kind | knowledge.KnowledgeCorpusKind | No | — | — | No | No | KnowledgeCorpusKind | Clase de corpus autorizado. | architecture.yml#rag_retrieval; architecture.yml#INV-010; SRC_ADR_007; DD-007 | — |
| title | text | No | — | — | No | No | — | Título de la fuente autorizada. | architecture.yml#rag_retrieval; architecture.yml#INV-010; SRC_ADR_007; DD-007 | — |
| provenance | text | No | — | — | No | No | — | Referencia obligatoria de origen autorizado; nunca URL con tokens o secretos. | architecture.yml#rag_retrieval; architecture.yml#INV-010; SRC_ADR_007; DD-007 | — |
| reviewed_incident_id | uuid | No | — | ops.incidents.id | Sí | No | — | Incidente revisado cuando el corpus es reviewed_incidents; elegibilidad RAG requiere separación evaluación. | architecture.yml#rag_retrieval; architecture.yml#INV-010; SRC_ADR_007; DD-007 | — |
| correlation_id | text | No | — | — | No | No | — | Identificador de correlación end-to-end; no contiene información sensible. | architecture.yml#CTRL-003 | — |
| created_at | timestamptz | No | — | — | No | No | — | Instante de persistencia; permite aplicar retención cuando corresponde. | SRC_ADR_013; DD-015 | A-002 |

### `knowledge.knowledge_chunks`

Chunks recuperables de documentos autorizados; conserva provenance y pgvector sin dimensión fija.

Owner: `rag_retrieval`. scope_basis: `approved_domain`. status: `confirmed`.

Fuentes: SRC_ADR_007, architecture.yml#INV-010, DD-009.

Claves únicas compuestas: `(document_id, chunk_index)`.

Checks: `chunk_index >= 0`; `btrim(provenance) <> ''`.

| Columna | Tipo | PK | FK | logical_ref | Nullable | Unique | Enum | Descripción | Fuente | Assumption |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| id | uuid | Sí | — | — | No | No | — | Identificador estable asignado por el servicio propietario. | SRC_ADR_007; architecture.yml#INV-010; DD-009 | A-001 |
| document_id | uuid | No | knowledge.knowledge_documents.id | — | No | Compuesto: (document_id, chunk_index) | — | Documento de procedencia; permite reconstruir fuentes. | SRC_ADR_007; architecture.yml#INV-010; DD-009 | — |
| chunk_index | integer | No | — | — | No | Compuesto: (document_id, chunk_index) | — | Posición del chunk dentro del documento. | SRC_ADR_007; architecture.yml#INV-010; DD-009 | A-009 |
| content | text | No | — | — | No | No | — | Fragmento autorizado y saneado; nunca casos/soluciones de evaluación. | SRC_ADR_007; architecture.yml#INV-010; DD-009 | — |
| provenance | text | No | — | — | No | No | — | Procedencia obligatoria del fragmento dentro de su documento. | SRC_ADR_007; architecture.yml#INV-010; DD-009 | — |
| embedding | vector | No | — | — | Sí | No | — | Embedding pgvector; dimensión abierta, sin vector(n). | SRC_ADR_007; architecture.yml#INV-010; DD-009 | — |
| correlation_id | text | No | — | — | No | No | — | Identificador de correlación end-to-end; no contiene información sensible. | architecture.yml#CTRL-003 | — |
| created_at | timestamptz | No | — | — | No | No | — | Instante de persistencia; permite aplicar retención cuando corresponde. | SRC_ADR_013; DD-015 | A-002 |

## Schema `audit`

Auditoría transversal funcional.

Owners permitidos: shared.

### `audit.audit_events`

Auditoría funcional transversal; before/after contienen solo metadata sanitizada, jamás logs crudos, secretos, tokens o credenciales.

Owner: `shared`. scope_basis: `approved_domain`. status: `confirmed`.

Fuentes: SRC_ADR_011, architecture.yml#audit_trail, architecture.yml#CTRL-002, DD-016.

| Columna | Tipo | PK | FK | logical_ref | Nullable | Unique | Enum | Descripción | Fuente | Assumption |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| id | uuid | Sí | — | — | No | No | — | Identificador estable asignado por el servicio propietario. | SRC_ADR_011; architecture.yml#audit_trail; architecture.yml#CTRL-002; DD-016 | A-001 |
| category | audit.AuditCategory | No | — | — | No | No | AuditCategory | Categoría funcional declarada en architecture.yml. | SRC_ADR_011; architecture.yml#audit_trail; architecture.yml#CTRL-002; DD-016 | — |
| correlation_id | text | No | — | — | No | No | — | Identificador de correlación end-to-end; no contiene información sensible. | architecture.yml#CTRL-003 | — |
| actor_ref | text | No | — | — | Sí | No | — | Identidad externa del actor cuando está disponible. | SRC_ADR_011; architecture.yml#audit_trail; architecture.yml#CTRL-002; DD-016 | — |
| entity_type | text | No | — | — | No | No | — | Tipo de objeto auditado; referencia polimórfica lógica. | SRC_ADR_011; architecture.yml#audit_trail; architecture.yml#CTRL-002; DD-016 | — |
| entity_id | text | No | — | — | No | No | — | ID lógico del objeto auditado; sin FK polimórfica. | SRC_ADR_011; architecture.yml#audit_trail; architecture.yml#CTRL-002; DD-016 | — |
| action | text | No | — | — | No | No | — | Acción funcional observada. | SRC_ADR_011; architecture.yml#audit_trail; architecture.yml#CTRL-002; DD-016 | — |
| before_state | jsonb | No | — | — | Sí | No | — | Solo metadata sanitizada previa; prohíbe raw logs/payload sensible no enmascarado. | SRC_ADR_011; architecture.yml#audit_trail; architecture.yml#CTRL-002; DD-016 | — |
| after_state | jsonb | No | — | — | Sí | No | — | Solo metadata sanitizada posterior; prohíbe secrets, tokens y credentials. | SRC_ADR_011; architecture.yml#audit_trail; architecture.yml#CTRL-002; DD-016 | — |
| occurred_at | timestamptz | No | — | — | No | No | — | Instante de ocurrencia del evento funcional. | SRC_ADR_011; architecture.yml#audit_trail; architecture.yml#CTRL-002; DD-016 | A-002 |
| created_at | timestamptz | No | — | — | No | No | — | Instante de persistencia; permite aplicar retención cuando corresponde. | SRC_ADR_013; DD-015 | A-002 |

## Enums

- `IncidentStatus`: OPEN, IN_REMEDIATION, VERIFICATION, RESOLVED.
- `DiagnosisStatus`: ANALYZING, DIAGNOSIS_READY, INCONCLUSIVE.
- `HumanReviewDecision`: CONFIRMED, CORRECTED, REJECTED.
- `IncidentRunRole`: ORIGIN, VERIFICATION.
- `PipelineStage`: BUILD, TESTING, QUALITY_GATE, DEPLOYMENT, CONTAINER, INFRASTRUCTURE.
- `MonitoringStatus`: ACTIVE, PAUSED.
- `AccessCapability`: VIEW, OPERATE, CONFIGURE.
- `Severity`: CRITICAL, HIGH, MEDIUM, LOW.
- `PipelineCriticality`: CRITICAL, HIGH, MEDIUM, LOW.
- `KnowledgeCorpusKind`: reviewed_incidents, authorized_technical_documentation, authorized_response_procedures.
- `AuditCategory`: diagnostic_generation, evidence_usage, human_review, access_and_governance_events.

## Decisiones de diseño

### DD-001 — Repository separado + Pipeline = monitored GitHub Actions workflow

- id: DD-001
- contexto: La IA presenta repositorio y workflow; el prompt aprueba su identidad de dominio.
- decisión: Repository es entidad propia, con relación 1:N Pipeline. Pipeline representa directamente un workflow monitorizado; no existe workflows.
- fuentes: Prompt aprobado §6.A; architecture.yml#pipeline_service; arquitectura-informacion.md.
- impacto: repositories y pipelines en ops, propiedad de pipeline_service; sin nuevas fronteras C4.
- reversibilidad: Separar workflows requeriría una nueva decisión y migración explícita.

### DD-002 — Incident con 1 ORIGIN + N VERIFICATION

- id: DD-002
- contexto: El incidente nace de exactamente una ejecución fallida; la verificación admite varias ejecuciones.
- decisión: incident_runs usa ORIGIN/VERIFICATION. Un índice parcial garantiza como máximo un ORIGIN; triggers diferidos exigen exactamente uno fallido al commit, con ORIGIN consistente con el pipeline del incidente. No se impone un workflow concreto a VERIFICATION. Se bloquea TRUNCATE de vínculos para preservar el invariante.
- fuentes: Prompt aprobado §6.B; SRC_ADR_010; SRC_ADR_018.
- impacto: Crear incidente y ORIGIN en la misma transacción; cambiar el ORIGIN o el pipeline revalida consistencia. La ejecución fallida es dato de GitHub, no un detector propio.
- reversibilidad: Cambiar cardinalidad o requisito de fallo requiere decisión aprobada y reemplazar constraints.

### DD-003 — Diagnosis append-only versionado

- id: DD-003
- contexto: El diagnóstico evoluciona sin reemplazar las hipótesis anteriores.
- decisión: Cada snapshot tiene versión positiva y única por incidente; actual = mayor versión. UPDATE/DELETE/TRUNCATE se rechazan. Cambiar estado también añade una versión. probable_cause puede ser null en ANALYZING/INCONCLUSIVE; DIAGNOSIS_READY exige causa probable y diagnosis_ready_at.
- fuentes: Prompt aprobado §6.C; architecture.yml#INV-005; SRC_ADR_013.
- impacto: Historial inmutable y lectura de última versión en aplicación. Una futura operación de retención necesita procedimiento controlado explícito; no se crea purge job.
- reversibilidad: Cambiar mutabilidad requiere nueva decisión; las hipótesis históricas pueden migrarse sin perder versiones.

### DD-004 — Recommendation entidad propia

- id: DD-004
- contexto: Una versión puede proponer varias recomendaciones trazables.
- decisión: diagnoses 1:N recommendations, con descripción y marcado crítico conforme al componente de gobierno humano. No se ejecuta remediación automática.
- fuentes: Prompt aprobado §6.D; SRC_ADR_016; architecture.yml#INV-007.
- impacto: FK dentro de diagnosis; recomendaciones no embebidas en un único payload diagnóstico.
- reversibilidad: Puede cambiar representación con migración que conserve diagnóstico y trazabilidad.

### DD-005 — Human review CONFIRMED/CORRECTED/REJECTED

- id: DD-005
- contexto: La IA antigua mezclaba rechazo con causa alternativa; el prompt y Human-in-the-Loop distinguen tres decisiones.
- decisión: CONFIRMED acepta; CORRECTED requiere causa corregida no vacía; REJECTED rechaza sin alternativa validada. PENDING se deriva de ausencia de revisión. Mapping contractual: diagnostic_id → diagnoses.id, reviewer → reviewer_ref, decision → decision, timestamp → timestamp, correlationId → correlation_id. actual_cause/comment son opcionales salvo la semántica CORRECTED.
- fuentes: Prompt aprobado §6.E; SRC_ADR_011; SRC_ADR_016; INV-006.
- impacto: No se persiste ValidationStatus ni PENDING. Se permite historial de revisiones sin imponer una decisión final de cardinalidad adicional. REJECTED con causa alternativa validada debe registrarse como CORRECTED.
- reversibilidad: Cambiar enum o cardinalidad exige decisión funcional y migración; la IA histórica se conserva.

### DD-006 — Blob por referencia, no contenido grande en PostgreSQL

- id: DD-006
- contexto: Los logs extensos viven en Azure Blob Storage; el diagnóstico debe conservar evidencia sustentante.
- decisión: evidence_items almacena metadata, summary y excerpt normalizados. storage_container/blob_object_key se informan juntos cuando existen. diagnosis_evidence_links identifica evidencia sustentante por ID lógico. No se guardan SAS, secretos, credenciales ni payload sensible crudo.
- fuentes: Prompt aprobado §6.F-G; architecture.yml#object_evidence_store; INV-001; INV-002; SRC_ADR_013.
- impacto: Permite recuperar el objeto externo con controles existentes; el hash no fija algoritmo. El saneamiento de contenido corresponde a aplicación.
- reversibilidad: Puede evolucionar la localización externa mediante migración de referencias sin duplicar logs en la base.

### DD-007 — diagnosis_source_links para trazabilidad RAG

- id: DD-007
- contexto: consulted_sources debe ser reconstruible por versión.
- decisión: diagnosis_source_links apunta lógicamente a knowledge_chunks; su FK intra-schema conduce a knowledge_documents. Documentos y chunks exigen provenance. Corpus limitado a reviewed_incidents, authorized_technical_documentation y authorized_response_procedures.
- fuentes: Prompt aprobado §6.H-I; architecture.yml#rag_retrieval; diagnostic_output; INV-010.
- impacto: No se incluyen casos de evaluación ni soluciones de referencia en knowledge. Elegibilidad del corpus se verifica en aplicación; texto/provenance no puede validarse semánticamente por una FK.
- reversibilidad: Puede añadirse otra estrategia de provenance mediante decisión posterior conservando la traza existente.

### DD-008 — Cross-schema logical references, sin FK física

- id: DD-008
- contexto: Una instancia compartida no implica ownership compartido ni acoplamiento entre contextos.
- decisión: Todas las referencias cross-schema son logical_ref. DBML no emite Ref ni SQL FOREIGN KEY para ellas. Se permite FK física intra-schema. No hay navegación JPA/ORM cross-context; referencias se resuelven por contratos existentes.
- fuentes: Prompt aprobado §10; SRC_ADR_018.
- impacto: La base no garantiza existencia de IDs remotos; cada owner valida referencias por APIs/eventos de architecture.yml. No se diseñan nuevas relaciones de comunicación.
- reversibilidad: Reversible: una futura decisión Accepted y migraciones podrían introducir FK cross-schema; nunca implícitamente.

### DD-009 — Vector sin dimensión fija

- id: DD-009
- contexto: Azure OpenAI Embeddings está aprobado, pero el modelo concreto no se ha fijado.
- decisión: knowledge_chunks.embedding usa vector sin dimensión. Se genera CREATE EXTENSION IF NOT EXISTS vector. embedding_dimension: null sigue en open_questions. chunk_index se supone base cero; embedding puede quedar null durante carga.
- fuentes: Prompt aprobado §6.I; SRC_ADR_007; DQ-003.
- impacto: No hay vector(1536), índice vectorial dependiente de dimensión ni mecanismo de actualización seleccionado.
- reversibilidad: Una futura elección de embedding requiere decisión y migración de tipo/datos/índices.

### DD-010 — Confidence sin escala cerrada

- id: DD-010
- contexto: La IA muestra un ejemplo numérico que no fija escala de persistencia.
- decisión: confidence JSONB nullable conserva valor o estructura recibidos; no tiene CHECK de rango ni escala numérica cerrada. La representación física es una suposición reversible, no la resolución de DQ-002.
- fuentes: Prompt aprobado §6.C; arquitectura-informacion.md#Confidence; DQ-002.
- impacto: No impone 0..1; consultas interpretan el valor solo conforme a un contrato posterior aprobado.
- reversibilidad: Puede migrarse a un tipo más específico cuando se aprueben escala y semántica.

### DD-011 — CQRS lógico, sin Event Sourcing

- id: DD-011
- contexto: Se aprueba separar commands y queries en aplicación manteniendo persistencia común.
- decisión: Command → Handler/Service → Domain → Repository → PostgreSQL. Query → Handler/Service → Query Repository/Projection → PostgreSQL. Sin Event Sourcing ni Event Store, sin bases físicas de lectura/escritura.
- fuentes: Prompt aprobado §0.E-F; SRC_ADR_018.
- impacto: No se crean SQL views CQRS ni v_incident_queue. Historial diagnóstico y audit_events no son un Event Store.
- reversibilidad: Cambiar a separación física o Event Sourcing requiere nueva decisión arquitectónica.

### DD-012 — Ownership de datos por Bounded Context

- id: DD-012
- contexto: Se aprueban cinco schemas y repositorios independientes por microservicio.
- decisión: ops: pipeline_service; evidence_items: log_event_service; correlated_contexts: evidence_correlation_engine; diagnosis: recommendation_service; knowledge: rag_retrieval; audit: shared. Cada owner escribe solo sus tablas; compartir evidence no permite escribir las del otro servicio.
- fuentes: Prompt aprobado §0.D-G y §5; SRC_ADR_018; SRC_ADR_011.
- impacto: Schema/table ownership se valida contra containers/component parents existentes. No se crean servicios, users, teams ni roles PostgreSQL en esta iteración. Ingesta y NLP pueden mantener dominio ligero sin Aggregates artificiales.
- reversibilidad: Mover ownership requiere decisión explícita y migración; multirepo no se convierte a monorepo.

### DD-013 — Tipos, identidad y claves físicas mínimas

- id: DD-013
- contexto: El prompt aprueba conceptos, pero no concreta todos los tipos y claves físicas.
- decisión: UUID de servicio para PK, text para IDs externos y correlation_id, timestamptz para tiempos, boolean para marcado crítico/fallo, bigint para secuencia/tamaño. Claves compuestas previenen duplicación de workflows, intentos, etapas, chunks y vínculos. Severity y PipelineCriticality son enums distintos. PipelineStage reutilizado se materializa como enum local en cada schema para evitar dependencia física de tipos.
- fuentes: Prompt aprobado §6 y §8; SRC_ADR_018; A-001/A-002/A-003/A-004/A-009.
- impacto: No se fijan versiones Java/Spring/Python ni algoritmo UUID/hash. Solo se genera SQL con tipos PostgreSQL y constraints simples expresables en DBML. No hay taxonomía de log levels interna nueva.
- reversibilidad: Tipos y claves pueden revisarse con migración; identidad y alcance de entidades requieren aprobación explícita.

### DD-014 — Contexto correlacionado mínimo y ownership de evidencia

- id: DD-014
- contexto: Se requiere persistir contexto sin añadir una tabla de asociación no aprobada ni permitir escritura de evidencia ajena.
- decisión: correlated_contexts guarda incident_id/execution_id lógicos, evidence_ids UUID[] lógicos, summary y correlation_id. La colección conserva provenance operacional por los IDs de evidence_items. No se agrega payload crudo ni contexto sensible JSON.
- fuentes: architecture.yml#evidence_correlation_engine; SRC_ADR_015; Prompt §5; A-006.
- impacto: FK de arrays no se generan; aplicación valida referencias y evita fusionar ejecuciones no relacionadas. En ER toda referencia lógica es discontinua, incluida esta relación intra-schema entre owners.
- reversibilidad: Una relación normalizada exigiría aprobación para una tabla adicional y migración; colección es reversible.

### DD-015 — Retención y tiempos sin métricas duplicadas

- id: DD-015
- contexto: ADR-013 define 365 días para logs, diagnósticos y evidencias; TMD se deriva de timestamps.
- decisión: created_at permite retención de evidence_items, correlated_contexts, diagnoses, recommendations y vínculos/revisiones diagnósticas dependientes. detected_at/remediation_started_at/verification_started_at/resolved_at están en incidents; diagnosis_ready_at está en cada versión diagnóstica. TMD = diagnosis_ready_at − detected_at; MTTR puede calcularse secundariamente.
- fuentes: SRC_ADR_013; INV-009; Prompt §6.J y §12; A-002.
- impacto: No se persisten TMD/MTTR. No se extiende silenciosamente el plazo a configuración, corpus ni auditoría. Las consultas escogen la versión/periodo; no se fija una política nueva de agregación KPI. No hay purge jobs.
- reversibilidad: Cambiar retención necesita fuente corporativa/decisión; cambiar timestamps requiere migración explícita.

### DD-016 — Auditoría transversal sanitizada

- id: DD-016
- contexto: La auditoría persiste en PostgreSQL sin audit_service.
- decisión: audit_events conserva categorías exactas de architecture.yml, correlation_id, referencia externa al actor, referencia polimórfica a entidad, acción, estados JSONB opcionales y tiempos. before_state/after_state contienen exclusivamente metadata sanitizada.
- fuentes: SRC_ADR_011; architecture.yml#audit_trail; CTRL-002; Prompt §11.
- impacto: No se registran logs crudos, secretos, tokens, credenciales ni payload sensible no enmascarado. No hay FK polimórfica; saneamiento se valida en aplicación y no se presume garantizado por el tipo JSONB.
- reversibilidad: El formato sanitizado puede evolucionar con contratos aprobados; no habilita Event Sourcing.

### DD-017 — Pipeline access grants IA-only/inferred

- id: DD-017
- contexto: Las capacidades VIEW/OPERATE/CONFIGURE derivan principalmente de arquitectura de información.
- decisión: pipeline_access_grants conserva scope_basis: ia_only y status: inferred; referencia principal Entra ID sin users/roles internos. Es representación provisional, no implementación final RBAC ni requisito core.
- fuentes: arquitectura-informacion.md; SRC_ADR_003; Prompt §7; DQ-005/DQ-006.
- impacto: Se muestra con borde punteado y etiqueta IA-only / inferred; la política de alta de workflows y RBAC siguen abiertas.
- reversibilidad: Puede retirarse o cambiarse cuando se apruebe implementación definitiva; nunca promoverla automáticamente.

## Assumptions

- **A-001** (assumption): UUID asignados por cada servicio; no default ni extensión generadora de UUID.
- **A-002** (assumption): Tiempos en timestamptz; created_at asignado por el owner. diagnosis_ready_at pertenece a cada versión; no se duplica en ops.incidents ni se almacena TMD.
- **A-003** (assumption): IDs externos GitHub como text, run_attempt positivo; claves únicas por repositorio/workflow y pipeline/run/attempt.
- **A-004** (assumption): failed representa el fallo ya identificado por GitHub Actions; no fija un algoritmo nuevo de detección ni una taxonomía interna de resultados.
- **A-005** (assumption): Severity nullable mientras no exista regla aprobada de derivación; no derivar de criticality ni de log level.
- **A-006** (assumption): correlated_contexts conserva evidence_ids UUID[] como referencias lógicas al owner log_event_service; validación y saneamiento en aplicación, sin tabla de asociación adicional.
- **A-007** (assumption): probable_cause nullable para snapshots ANALYZING/INCONCLUSIVE; DIAGNOSIS_READY exige causa probable y diagnosis_ready_at. Cambiar estado añade una versión inmutable.
- **A-008** (assumption): confidence JSONB nullable conserva el valor recibido sin fijar escala, unidad ni representación numérica obligatoria.
- **A-009** (assumption): chunk_index empieza en cero y es único por documento; embedding nullable durante carga, sin resolver mecanismo de actualización.
- **A-010** (assumption): El corpus elegible y las referencias lógicas son verificados por los owners en aplicación; constraints estructurales no pueden detectar texto de evaluación ni datos sensibles dentro de texto/JSON.
- **A-011** (assumption): No hay originales Charter/TI/drift en el checkout; las referencias a alcance provienen del modelo canónico vigente y del prompt aprobado, sin atribuir nuevos requisitos literales al Charter.
- **A-012** (assumption): Sin cardinalidad final adicional para revisiones: se admite historial de human_reviews por versión; la ausencia implica PENDING y no se agrega enum persistido de validación.

## Open Questions

- **DQ-001 / incident_severity_derivation** (open_question): Regla concreta de derivación de severidad del incidente.
- **DQ-002 / confidence_semantics** (open_question): Escala y semántica exacta de confidence.
- **DQ-003 / embedding_dimension** (open_question): Dimensión del embedding; el modelo concreto sigue sin fijarse. `embedding_dimension: null`.
- **DQ-004 / rag_corpus_updates** (open_question): Mecanismo definitivo de carga y actualización del corpus RAG.
- **DQ-005 / pipeline_rbac** (open_question): Implementación final de RBAC granular por pipeline.
- **DQ-006 / monitored_workflow_registration** (open_question): Política funcional final para alta de workflows monitorizados.

## IA-only / inferred

- `ops.pipeline_access_grants`: ia_only / inferred. Representación provisional de capacidades por pipeline; no requisito core ni implementación definitiva RBAC. Fuentes: docs/research/arquitectura-informacion.md, SRC_ADR_003, DD-017.
