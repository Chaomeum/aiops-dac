# Arquitectura física para sustentación

Generado desde `model/physical_presentation.yml`; hechos de `model/architecture.yml`.

Diseño propuesto; las figuras no acreditan implementación o despliegue actual.
Los iconos proceden del paquete diagrams instalado; los SVG los incluyen embebidos.
Las agrupaciones son columnas de lectura, no subredes ni nuevos recursos Azure.
Cada nodo declara su propia tecnología. Los componentes internos del diagnóstico se agrupan explícitamente en su contenedor.
PostgreSQL/pgvector representan roles de una sola instancia física (ADR-018); no se confirma un producto Azure para PostgreSQL.
Los protocolos están en los tooltips SVG y en la tabla inferior. Las respuestas síncronas regresan por la misma llamada.

## Física 01 — Fuentes, ingesta y mensajería

[SVG](fisica_expo_01.svg) · [PNG para diapositivas](fisica_expo_01.png)

7 nodos. GitHub Actions y Azure Monitor aportan evidencia autorizada. Ingesta, cuyo diseño especifica Java y Spring Boot sobre Azure Container Apps, protege y normaliza los datos antes de Service Bus. Un topic distribuye los eventos a tres suscripciones: Pipeline Service, Log/Event Service y NLP; este último continúa en la segunda vista. El acceso a GitHub es read-only.

Service Bus entrega también eventos a NLP (vista 02). Persistencia y acceso: vista 03.

| Relación canónica | Protocolo |
|---|---|
| Emite eventos autorizados del workflow | HTTPS/Webhook |
| Entrega eventos de ejecución para registrar contexto del pipeline | Azure Service Bus |
| Entrega evidencia normalizada para registro y consulta | Azure Service Bus |
| Recupera logs, artefactos y metadatos autorizados | GitHub API/HTTPS |
| Publica evidencia normalizada y protegida | Azure Service Bus |
| Proporciona repositorio, commits y definición de workflows CI/CD | GitHub API/HTTPS |
| Proporciona telemetría y evidencia operacional autorizada | REST/HTTPS |

## Física 02 — Runtime del diagnóstico asistido

[SVG](fisica_expo_02.svg) · [PNG para diapositivas](fisica_expo_02.png)

7 nodos. NLP y RAG usan Python y FastAPI; correlación y diagnóstico usan Java y Spring Boot. Los cuatro servicios tienen runtime propio en Azure Container Apps. NLP utiliza Drain3. Diagnóstico orquesta RAG, que consulta pgvector sobre PostgreSQL, y solicita inferencia a Azure OpenAI, familia GPT-4 sin modelo concreto fijado. Azure OpenAI es externo y no se aloja en Container Apps.

Entrada desde vista 01. PostgreSQL/pgvector: misma instancia física. Consumo y revisión: vista 03.

| Relación canónica | Protocolo |
|---|---|
| Entrega eventos normalizados para procesamiento | Azure Service Bus |
| Entrega logs y evidencia procesada para correlación | REST/HTTPS |
| Recupera conocimiento operacional semánticamente relacionado | PostgreSQL/pgvector |
| Entrega contexto correlacionado del incidente para diagnóstico asistido | REST/HTTPS |
| Solicita conocimiento contextual autorizado para el incidente | REST/HTTPS |
| Solicita inferencia diagnóstica con evidencia saneada y contexto RAG | Azure OpenAI API/HTTPS |

## Física 03 — Acceso, persistencia y revisión humana

[SVG](fisica_expo_03.svg) · [PNG para diapositivas](fisica_expo_03.png)

10 nodos. El dashboard React y TypeScript se aloja en Azure Static Web Apps. Entra ID autentica y APIM protege y enruta las APIs; ninguno se despliega en Container Apps. Los servicios mantienen datos estructurados en PostgreSQL y evidencias extensas en Azure Blob Storage. La revisión humana se registra dentro del servicio diagnóstico. El workflow publica el artifact con su paso nativo.

Actions recupera el diagnóstico por APIM y publica su artifact. Revisión humana dentro del servicio diagnóstico.

| Relación canónica | Protocolo |
|---|---|
| Persiste pipelines, etapas, estados y metadatos de ejecución | PostgreSQL |
| Persiste y consulta metadatos y referencias de evidencia normalizada | PostgreSQL |
| Almacena y resuelve referencias de logs extensos y evidencias | Object Storage API |
| Persiste diagnóstico, recomendaciones y vínculos con evidencia | PostgreSQL |
| Consulta resultados y registra revisión humana | HTTPS |
| Autentica usuarios corporativos | OIDC/OAuth2/HTTPS |
| Consume APIs protegidas del prototipo | REST/HTTPS |
| Enruta consultas de pipelines y ejecuciones | REST/HTTPS |
| Enruta consultas de logs, eventos y evidencias | REST/HTTPS |
| Enruta consultas y operaciones de diagnóstico y revisión | REST/HTTPS |
| Persiste decisiones y trazabilidad de revisión humana | PostgreSQL |
| Consulta diagnostic_output para publicar el artifact del workflow | REST/HTTPS |

## Relaciones entre vistas

- `rel_correlation_postgresql`: Servicio de Correlación de Evidencias → PostgreSQL: Registra contexto correlacionado y trazabilidad (PostgreSQL).

## Advertencias

Iconos de fallback: []

Modelo concreto GPT-4 y modelo de embeddings sin fijar en el SSOT. No se introduce una selección.
