# Arquitectura lógica para sustentación

Generado desde `model/logical_presentation.yml`, con hechos de `model/architecture.yml`.

Diseño propuesto; estas figuras no acreditan implementación. Lectura de izquierda a derecha.

Los componentes internos del servicio diagnóstico se agrupan explícitamente en su contenedor.
Se omiten conexiones que salen de cada vista; las notas indican su continuación.
PostgreSQL y pgvector son roles lógicos de una misma instancia física según ADR-018.

## Logical View 01 — Evidence Intake and Distribution

[Abrir SVG](logica_expo_01.svg) · [PNG para diapositivas](logica_expo_01.png)

7 nodos. GitHub Actions origina eventos de ejecuciones fallidas. Ingesta consulta evidencia autorizada, la normaliza y protege antes de publicarla en Service Bus. Pipeline Service, Log/Event Service y NLP consumen suscripciones independientes; NLP continúa en la segunda vista.

Service Bus also delivers events to NLP (view 02). Persistence and queries: view 03.

## Logical View 02 — Assisted Diagnosis

[Abrir SVG](logica_expo_02.svg) · [PNG para diapositivas](logica_expo_02.png)

7 nodos. NLP entrega evidencia procesada a correlación. Diagnostic & Recommendation Service recibe el contexto del incidente, recupera conocimiento autorizado mediante RAG y solicita inferencia a Azure OpenAI. La respuesta es una causa probable con evidencia y recomendaciones; no ejecuta remediación autónoma.

Input from view 01. Diagnosis persistence, querying and human review: view 03.

## Logical View 03 — Consumption and Human Review

[Abrir SVG](logica_expo_03.svg) · [PNG para diapositivas](logica_expo_03.png)

10 nodos. Los usuarios se autentican con Entra ID y consumen el dashboard mediante APIs protegidas por APIM. Los servicios consultan y conservan contexto, evidencia, diagnósticos y revisión humana. GitHub Actions recupera el diagnóstico mediante APIM y publica el artifact con un paso nativo.

Services from views 01/02 reappear as the same elements. Actions publishes its own artifact.

## Relaciones representadas y protocolos

Las cajas de agrupación organizan la lectura; no son nuevos elementos arquitectónicos.

| Relación canónica | Protocolo | Vistas |
|---|---|---|
| Emits authorized workflow events | HTTPS/Webhook | logica_expo_01 |
| Delivers execution events to register pipeline context | Azure Service Bus | logica_expo_01 |
| Delivers normalized evidence for registration and querying | Azure Service Bus | logica_expo_01 |
| Persists pipelines, stages, states and execution metadata | PostgreSQL | logica_expo_03 |
| Persists and queries normalized evidence metadata and references | PostgreSQL | logica_expo_03 |
| Stores and resolves references to large logs and evidence | Object Storage API | logica_expo_03 |
| Persists diagnosis, recommendations and evidence links | PostgreSQL | logica_expo_03 |
| Retrieves authorized logs, artifacts and metadata | GitHub API/HTTPS | logica_expo_01 |
| Publishes normalized and protected evidence | Azure Service Bus | logica_expo_01 |
| Delivers normalized events for processing | Azure Service Bus | logica_expo_02 |
| Delivers logs and processed evidence for correlation | REST/HTTPS | logica_expo_02 |
| Retrieves semantically related operational knowledge | PostgreSQL/pgvector | logica_expo_02 |
| Provides the repository, commits and CI/CD workflow definitions | GitHub API/HTTPS | logica_expo_01 |
| Provides authorized telemetry and operational evidence | REST/HTTPS | logica_expo_01 |
| Queries results and records human review | HTTPS | logica_expo_03 |
| Delivers correlated incident context for assisted diagnosis | REST/HTTPS | logica_expo_02 |
| Requests authorized contextual knowledge for the incident | REST/HTTPS | logica_expo_02 |
| Requests diagnostic inference with sanitized evidence and RAG context | Azure OpenAI API/HTTPS | logica_expo_02 |
| Authenticates corporate users | OIDC/OAuth2/HTTPS | logica_expo_03 |
| Consumes protected prototype APIs | REST/HTTPS | logica_expo_03 |
| Routes pipeline and execution queries | REST/HTTPS | logica_expo_03 |
| Routes log, event and evidence queries | REST/HTTPS | logica_expo_03 |
| Routes diagnosis and review queries and operations | REST/HTTPS | logica_expo_03 |
| Persists human review decisions and traceability | PostgreSQL | logica_expo_03 |
| Queries diagnostic_output to publish the workflow artifact | REST/HTTPS | logica_expo_03 |

## Relaciones entre vistas

- `rel_correlation_postgresql`: Evidence Correlation Service → PostgreSQL: Records correlated context and traceability (PostgreSQL).
