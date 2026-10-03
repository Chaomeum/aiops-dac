# Decisiones del modelo de dominio persistente

SSOT: `model/domain.yml`. `model/db.dbml` es una salida generada en esta iteración, al igual que SQL, el único ER y el diccionario. Las decisiones de aplicación aprobadas están en ADR-018 (Accepted, 2026-10-03).

Autoridad por materia: Project Charter para alcance; INV-*, ADR Accepted y architecture.yml para arquitectura vigente; tech_drift_resolutions y ADR tecnológicos para tecnología; arquitectura-informacion.md para derivaciones funcionales dentro de esos límites. No se usa una precedencia lineal ni se promueven propuestas IA a requisitos core. Los originales Charter/TI/drift no están presentes en este checkout (A-011); no se afirma haberlos leído ni se les atribuyen requisitos adicionales.

Las decisiones físicas adicionales DD-013 a DD-017 y las assumptions se explicitan como implementaciones reversibles dentro del alcance aprobado. Las seis preguntas abiertas permanecen en domain.yml.

Generación: `make validate` y `make db`; `make all` conserva physical/logical/C4 y añade db. Dependencias presentes: PyYAML 6.0.3, D2 0.9.0, @dbml/cli 10.2.0 sobre Node 24.21.0. Reproducibilidad exige las mismas versiones. No se instala PostgreSQL ni pgvector. Sintaxis de referencia: [DBML](https://dbml.dbdiagram.io/docs/) y [D2 SQL tables](https://d2lang.com/tour/sql-tables/).

## DD-001 — Repository separado + Pipeline = monitored GitHub Actions workflow

- id: DD-001
- contexto: La IA presenta repositorio y workflow; el prompt aprueba su identidad de dominio.
- decisión: Repository es entidad propia, con relación 1:N Pipeline. Pipeline representa directamente un workflow monitorizado; no existe workflows.
- fuentes: Prompt aprobado §6.A; architecture.yml#pipeline_service; arquitectura-informacion.md.
- impacto: repositories y pipelines en ops, propiedad de pipeline_service; sin nuevas fronteras C4.
- reversibilidad: Separar workflows requeriría una nueva decisión y migración explícita.

## DD-002 — Incident con 1 ORIGIN + N VERIFICATION

- id: DD-002
- contexto: El incidente nace de exactamente una ejecución fallida; la verificación admite varias ejecuciones.
- decisión: incident_runs usa ORIGIN/VERIFICATION. Un índice parcial garantiza como máximo un ORIGIN; triggers diferidos exigen exactamente uno fallido al commit, con ORIGIN consistente con el pipeline del incidente. No se impone un workflow concreto a VERIFICATION. Se bloquea TRUNCATE de vínculos para preservar el invariante.
- fuentes: Prompt aprobado §6.B; SRC_ADR_010; SRC_ADR_018.
- impacto: Crear incidente y ORIGIN en la misma transacción; cambiar el ORIGIN o el pipeline revalida consistencia. La ejecución fallida es dato de GitHub, no un detector propio.
- reversibilidad: Cambiar cardinalidad o requisito de fallo requiere decisión aprobada y reemplazar constraints.

## DD-003 — Diagnosis append-only versionado

- id: DD-003
- contexto: El diagnóstico evoluciona sin reemplazar las hipótesis anteriores.
- decisión: Cada snapshot tiene versión positiva y única por incidente; actual = mayor versión. UPDATE/DELETE/TRUNCATE se rechazan. Cambiar estado también añade una versión. probable_cause puede ser null en ANALYZING/INCONCLUSIVE; DIAGNOSIS_READY exige causa probable y diagnosis_ready_at.
- fuentes: Prompt aprobado §6.C; architecture.yml#INV-005; SRC_ADR_013.
- impacto: Historial inmutable y lectura de última versión en aplicación. Una futura operación de retención necesita procedimiento controlado explícito; no se crea purge job.
- reversibilidad: Cambiar mutabilidad requiere nueva decisión; las hipótesis históricas pueden migrarse sin perder versiones.

## DD-004 — Recommendation entidad propia

- id: DD-004
- contexto: Una versión puede proponer varias recomendaciones trazables.
- decisión: diagnoses 1:N recommendations, con descripción y marcado crítico conforme al componente de gobierno humano. No se ejecuta remediación automática.
- fuentes: Prompt aprobado §6.D; SRC_ADR_016; architecture.yml#INV-007.
- impacto: FK dentro de diagnosis; recomendaciones no embebidas en un único payload diagnóstico.
- reversibilidad: Puede cambiar representación con migración que conserve diagnóstico y trazabilidad.

## DD-005 — Human review CONFIRMED/CORRECTED/REJECTED

- id: DD-005
- contexto: La IA antigua mezclaba rechazo con causa alternativa; el prompt y Human-in-the-Loop distinguen tres decisiones.
- decisión: CONFIRMED acepta; CORRECTED requiere causa corregida no vacía; REJECTED rechaza sin alternativa validada. PENDING se deriva de ausencia de revisión. Mapping contractual: diagnostic_id → diagnoses.id, reviewer → reviewer_ref, decision → decision, timestamp → timestamp, correlationId → correlation_id. actual_cause/comment son opcionales salvo la semántica CORRECTED.
- fuentes: Prompt aprobado §6.E; SRC_ADR_011; SRC_ADR_016; INV-006.
- impacto: No se persiste ValidationStatus ni PENDING. Se permite historial de revisiones sin imponer una decisión final de cardinalidad adicional. REJECTED con causa alternativa validada debe registrarse como CORRECTED.
- reversibilidad: Cambiar enum o cardinalidad exige decisión funcional y migración; la IA histórica se conserva.

## DD-006 — Blob por referencia, no contenido grande en PostgreSQL

- id: DD-006
- contexto: Los logs extensos viven en Azure Blob Storage; el diagnóstico debe conservar evidencia sustentante.
- decisión: evidence_items almacena metadata, summary y excerpt normalizados. storage_container/blob_object_key se informan juntos cuando existen. diagnosis_evidence_links identifica evidencia sustentante por ID lógico. No se guardan SAS, secretos, credenciales ni payload sensible crudo.
- fuentes: Prompt aprobado §6.F-G; architecture.yml#object_evidence_store; INV-001; INV-002; SRC_ADR_013.
- impacto: Permite recuperar el objeto externo con controles existentes; el hash no fija algoritmo. El saneamiento de contenido corresponde a aplicación.
- reversibilidad: Puede evolucionar la localización externa mediante migración de referencias sin duplicar logs en la base.

## DD-007 — diagnosis_source_links para trazabilidad RAG

- id: DD-007
- contexto: consulted_sources debe ser reconstruible por versión.
- decisión: diagnosis_source_links apunta lógicamente a knowledge_chunks; su FK intra-schema conduce a knowledge_documents. Documentos y chunks exigen provenance. Corpus limitado a reviewed_incidents, authorized_technical_documentation y authorized_response_procedures.
- fuentes: Prompt aprobado §6.H-I; architecture.yml#rag_retrieval; diagnostic_output; INV-010.
- impacto: No se incluyen casos de evaluación ni soluciones de referencia en knowledge. Elegibilidad del corpus se verifica en aplicación; texto/provenance no puede validarse semánticamente por una FK.
- reversibilidad: Puede añadirse otra estrategia de provenance mediante decisión posterior conservando la traza existente.

## DD-008 — Cross-schema logical references, sin FK física

- id: DD-008
- contexto: Una instancia compartida no implica ownership compartido ni acoplamiento entre contextos.
- decisión: Todas las referencias cross-schema son logical_ref. DBML no emite Ref ni SQL FOREIGN KEY para ellas. Se permite FK física intra-schema. No hay navegación JPA/ORM cross-context; referencias se resuelven por contratos existentes.
- fuentes: Prompt aprobado §10; SRC_ADR_018.
- impacto: La base no garantiza existencia de IDs remotos; cada owner valida referencias por APIs/eventos de architecture.yml. No se diseñan nuevas relaciones de comunicación.
- reversibilidad: Reversible: una futura decisión Accepted y migraciones podrían introducir FK cross-schema; nunca implícitamente.

## DD-009 — Vector sin dimensión fija

- id: DD-009
- contexto: Azure OpenAI Embeddings está aprobado, pero el modelo concreto no se ha fijado.
- decisión: knowledge_chunks.embedding usa vector sin dimensión. Se genera CREATE EXTENSION IF NOT EXISTS vector. embedding_dimension: null sigue en open_questions. chunk_index se supone base cero; embedding puede quedar null durante carga.
- fuentes: Prompt aprobado §6.I; SRC_ADR_007; DQ-003.
- impacto: No hay vector(1536), índice vectorial dependiente de dimensión ni mecanismo de actualización seleccionado.
- reversibilidad: Una futura elección de embedding requiere decisión y migración de tipo/datos/índices.

## DD-010 — Confidence sin escala cerrada

- id: DD-010
- contexto: La IA muestra un ejemplo numérico que no fija escala de persistencia.
- decisión: confidence JSONB nullable conserva valor o estructura recibidos; no tiene CHECK de rango ni escala numérica cerrada. La representación física es una suposición reversible, no la resolución de DQ-002.
- fuentes: Prompt aprobado §6.C; arquitectura-informacion.md#Confidence; DQ-002.
- impacto: No impone 0..1; consultas interpretan el valor solo conforme a un contrato posterior aprobado.
- reversibilidad: Puede migrarse a un tipo más específico cuando se aprueben escala y semántica.

## DD-011 — CQRS lógico, sin Event Sourcing

- id: DD-011
- contexto: Se aprueba separar commands y queries en aplicación manteniendo persistencia común.
- decisión: Command → Handler/Service → Domain → Repository → PostgreSQL. Query → Handler/Service → Query Repository/Projection → PostgreSQL. Sin Event Sourcing ni Event Store, sin bases físicas de lectura/escritura.
- fuentes: Prompt aprobado §0.E-F; SRC_ADR_018.
- impacto: No se crean SQL views CQRS ni v_incident_queue. Historial diagnóstico y audit_events no son un Event Store.
- reversibilidad: Cambiar a separación física o Event Sourcing requiere nueva decisión arquitectónica.

## DD-012 — Ownership de datos por Bounded Context

- id: DD-012
- contexto: Se aprueban cinco schemas y repositorios independientes por microservicio.
- decisión: ops: pipeline_service; evidence_items: log_event_service; correlated_contexts: evidence_correlation_engine; diagnosis: recommendation_service; knowledge: rag_retrieval; audit: shared. Cada owner escribe solo sus tablas; compartir evidence no permite escribir las del otro servicio.
- fuentes: Prompt aprobado §0.D-G y §5; SRC_ADR_018; SRC_ADR_011.
- impacto: Schema/table ownership se valida contra containers/component parents existentes. No se crean servicios, users, teams ni roles PostgreSQL en esta iteración. Ingesta y NLP pueden mantener dominio ligero sin Aggregates artificiales.
- reversibilidad: Mover ownership requiere decisión explícita y migración; multirepo no se convierte a monorepo.

## DD-013 — Tipos, identidad y claves físicas mínimas

- id: DD-013
- contexto: El prompt aprueba conceptos, pero no concreta todos los tipos y claves físicas.
- decisión: UUID de servicio para PK, text para IDs externos y correlation_id, timestamptz para tiempos, boolean para marcado crítico/fallo, bigint para secuencia/tamaño. Claves compuestas previenen duplicación de workflows, intentos, etapas, chunks y vínculos. Severity y PipelineCriticality son enums distintos. PipelineStage reutilizado se materializa como enum local en cada schema para evitar dependencia física de tipos.
- fuentes: Prompt aprobado §6 y §8; SRC_ADR_018; A-001/A-002/A-003/A-004/A-009.
- impacto: No se fijan versiones Java/Spring/Python ni algoritmo UUID/hash. Solo se genera SQL con tipos PostgreSQL y constraints simples expresables en DBML. No hay taxonomía de log levels interna nueva.
- reversibilidad: Tipos y claves pueden revisarse con migración; identidad y alcance de entidades requieren aprobación explícita.

## DD-014 — Contexto correlacionado mínimo y ownership de evidencia

- id: DD-014
- contexto: Se requiere persistir contexto sin añadir una tabla de asociación no aprobada ni permitir escritura de evidencia ajena.
- decisión: correlated_contexts guarda incident_id/execution_id lógicos, evidence_ids UUID[] lógicos, summary y correlation_id. La colección conserva provenance operacional por los IDs de evidence_items. No se agrega payload crudo ni contexto sensible JSON.
- fuentes: architecture.yml#evidence_correlation_engine; SRC_ADR_015; Prompt §5; A-006.
- impacto: FK de arrays no se generan; aplicación valida referencias y evita fusionar ejecuciones no relacionadas. En ER toda referencia lógica es discontinua, incluida esta relación intra-schema entre owners.
- reversibilidad: Una relación normalizada exigiría aprobación para una tabla adicional y migración; colección es reversible.

## DD-015 — Retención y tiempos sin métricas duplicadas

- id: DD-015
- contexto: ADR-013 define 365 días para logs, diagnósticos y evidencias; TMD se deriva de timestamps.
- decisión: created_at permite retención de evidence_items, correlated_contexts, diagnoses, recommendations y vínculos/revisiones diagnósticas dependientes. detected_at/remediation_started_at/verification_started_at/resolved_at están en incidents; diagnosis_ready_at está en cada versión diagnóstica. TMD = diagnosis_ready_at − detected_at; MTTR puede calcularse secundariamente.
- fuentes: SRC_ADR_013; INV-009; Prompt §6.J y §12; A-002.
- impacto: No se persisten TMD/MTTR. No se extiende silenciosamente el plazo a configuración, corpus ni auditoría. Las consultas escogen la versión/periodo; no se fija una política nueva de agregación KPI. No hay purge jobs.
- reversibilidad: Cambiar retención necesita fuente corporativa/decisión; cambiar timestamps requiere migración explícita.

## DD-016 — Auditoría transversal sanitizada

- id: DD-016
- contexto: La auditoría persiste en PostgreSQL sin audit_service.
- decisión: audit_events conserva categorías exactas de architecture.yml, correlation_id, referencia externa al actor, referencia polimórfica a entidad, acción, estados JSONB opcionales y tiempos. before_state/after_state contienen exclusivamente metadata sanitizada.
- fuentes: SRC_ADR_011; architecture.yml#audit_trail; CTRL-002; Prompt §11.
- impacto: No se registran logs crudos, secretos, tokens, credenciales ni payload sensible no enmascarado. No hay FK polimórfica; saneamiento se valida en aplicación y no se presume garantizado por el tipo JSONB.
- reversibilidad: El formato sanitizado puede evolucionar con contratos aprobados; no habilita Event Sourcing.

## DD-017 — Pipeline access grants IA-only/inferred

- id: DD-017
- contexto: Las capacidades VIEW/OPERATE/CONFIGURE derivan principalmente de arquitectura de información.
- decisión: pipeline_access_grants conserva scope_basis: ia_only y status: inferred; referencia principal Entra ID sin users/roles internos. Es representación provisional, no implementación final RBAC ni requisito core.
- fuentes: arquitectura-informacion.md; SRC_ADR_003; Prompt §7; DQ-005/DQ-006.
- impacto: Se muestra con borde punteado y etiqueta IA-only / inferred; la política de alta de workflows y RBAC siguen abiertas.
- reversibilidad: Puede retirarse o cambiarse cuando se apruebe implementación definitiva; nunca promoverla automáticamente.
