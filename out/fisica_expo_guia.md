# Arquitectura física para sustentación

Generado desde `model/physical_presentation.yml`; hechos de `model/architecture.yml`.

Diseño propuesto; las figuras no acreditan implementación o despliegue actual.
Los iconos proceden del paquete diagrams instalado; los SVG los incluyen embebidos.
Las agrupaciones son columnas de lectura, no subredes ni nuevos recursos Azure.
Cada nodo declara su propia tecnología. Los componentes internos del diagnóstico se agrupan explícitamente en su contenedor.
PostgreSQL/pgvector representan roles de una sola instancia física (ADR-018); no se confirma un producto Azure para PostgreSQL.
Los protocolos están en los tooltips SVG y en la tabla inferior. Las respuestas síncronas regresan por la misma llamada.

## Physical View 01 — Sources, Ingestion and Messaging

[SVG](fisica_expo_01.svg) · [PNG para diapositivas](fisica_expo_01.png)

7 nodos. GitHub Actions y Azure Monitor aportan evidencia autorizada. Ingesta, cuyo diseño especifica Java y Spring Boot sobre Azure Container Apps, protege y normaliza los datos antes de Service Bus. Un topic distribuye los eventos a tres suscripciones: Pipeline Service, Log/Event Service y NLP; este último continúa en la segunda vista. El acceso a GitHub es read-only.

Service Bus also delivers events to NLP (view 02). Persistence and access: view 03.

| Relación canónica | Protocolo |
|---|---|
| Emits authorized workflow events | HTTPS/Webhook |
| Delivers execution events to register pipeline context | Azure Service Bus |
| Delivers normalized evidence for registration and querying | Azure Service Bus |
| Retrieves authorized logs, artifacts and metadata | GitHub API/HTTPS |
| Publishes normalized and protected evidence | Azure Service Bus |
| Provides the repository, commits and CI/CD workflow definitions | GitHub API/HTTPS |
| Provides authorized telemetry and operational evidence | REST/HTTPS |

## Physical View 02 — Assisted Diagnosis Runtime

[SVG](fisica_expo_02.svg) · [PNG para diapositivas](fisica_expo_02.png)

7 nodos. NLP y RAG usan Python y FastAPI; correlación y diagnóstico usan Java y Spring Boot. Los cuatro servicios tienen runtime propio en Azure Container Apps. NLP utiliza Drain3. Diagnóstico orquesta RAG, que consulta pgvector sobre PostgreSQL, y solicita inferencia a Azure OpenAI, familia GPT-4 sin modelo concreto fijado. Azure OpenAI es externo y no se aloja en Container Apps.

Input from view 01. PostgreSQL/pgvector: the same physical instance. Consumption and review: view 03.

| Relación canónica | Protocolo |
|---|---|
| Delivers normalized events for processing | Azure Service Bus |
| Delivers logs and processed evidence for correlation | REST/HTTPS |
| Retrieves semantically related operational knowledge | PostgreSQL/pgvector |
| Delivers correlated incident context for assisted diagnosis | REST/HTTPS |
| Requests authorized contextual knowledge for the incident | REST/HTTPS |
| Requests diagnostic inference with sanitized evidence and RAG context | Azure OpenAI API/HTTPS |

## Physical View 03 — Access, Persistence and Human Review

[SVG](fisica_expo_03.svg) · [PNG para diapositivas](fisica_expo_03.png)

10 nodos. El dashboard React y TypeScript se aloja en Azure Static Web Apps. Entra ID autentica y APIM protege y enruta las APIs; ninguno se despliega en Container Apps. Los servicios mantienen datos estructurados en PostgreSQL y evidencias extensas en Azure Blob Storage. La revisión humana se registra dentro del servicio diagnóstico. El workflow publica el artifact con su paso nativo.

Actions retrieves the diagnosis through APIM and publishes its artifact. Human review is within the diagnostic service.

| Relación canónica | Protocolo |
|---|---|
| Persists pipelines, stages, states and execution metadata | PostgreSQL |
| Persists and queries normalized evidence metadata and references | PostgreSQL |
| Stores and resolves references to large logs and evidence | Object Storage API |
| Persists diagnosis, recommendations and evidence links | PostgreSQL |
| Queries results and records human review | HTTPS |
| Authenticates corporate users | OIDC/OAuth2/HTTPS |
| Consumes protected prototype APIs | REST/HTTPS |
| Routes pipeline and execution queries | REST/HTTPS |
| Routes log, event and evidence queries | REST/HTTPS |
| Routes diagnosis and review queries and operations | REST/HTTPS |
| Persists human review decisions and traceability | PostgreSQL |
| Queries diagnostic_output to publish the workflow artifact | REST/HTTPS |

## Relaciones entre vistas

- `rel_correlation_postgresql`: Evidence Correlation Service → PostgreSQL: Records correlated context and traceability (PostgreSQL).

## Advertencias

Iconos de fallback: []

Modelo concreto GPT-4 y modelo de embeddings sin fijar en el SSOT. No se introduce una selección.
