# Arquitectura lógica para sustentación

Generado desde `model/logical_presentation.yml`, con hechos de `model/architecture.yml`.

Diseño propuesto; estas figuras no acreditan implementación. Lectura de izquierda a derecha.

Los componentes internos del servicio diagnóstico se agrupan explícitamente en su contenedor.
Se omiten conexiones que salen de cada vista; las notas indican su continuación.
PostgreSQL y pgvector son roles lógicos de una misma instancia física según ADR-018.

## Lógica 01 — Entrada y distribución de evidencia

[Abrir SVG](logica_expo_01.svg) · [PNG para diapositivas](logica_expo_01.png)

7 nodos. GitHub Actions origina eventos de ejecuciones fallidas. Ingesta consulta evidencia autorizada, la normaliza y protege antes de publicarla en Service Bus. Pipeline Service, Log/Event Service y NLP consumen suscripciones independientes; NLP continúa en la segunda vista.

Service Bus entrega también eventos a NLP (vista 02). Persistencia y consultas: vista 03.

## Lógica 02 — Diagnóstico asistido

[Abrir SVG](logica_expo_02.svg) · [PNG para diapositivas](logica_expo_02.png)

7 nodos. NLP entrega evidencia procesada a correlación. Diagnostic & Recommendation Service recibe el contexto del incidente, recupera conocimiento autorizado mediante RAG y solicita inferencia a Azure OpenAI. La respuesta es una causa probable con evidencia y recomendaciones; no ejecuta remediación autónoma.

Entrada desde vista 01. Persistencia, consulta y revisión humana del diagnóstico: vista 03.

## Lógica 03 — Consumo y revisión humana

[Abrir SVG](logica_expo_03.svg) · [PNG para diapositivas](logica_expo_03.png)

10 nodos. Los usuarios se autentican con Entra ID y consumen el dashboard mediante APIs protegidas por APIM. Los servicios consultan y conservan contexto, evidencia, diagnósticos y revisión humana. GitHub Actions recupera el diagnóstico mediante APIM y publica el artifact con un paso nativo.

Los servicios de vistas 01/02 reaparecen como los mismos elementos. Actions publica su propio artifact.

## Relaciones representadas y protocolos

Las cajas de agrupación organizan la lectura; no son nuevos elementos arquitectónicos.

| Relación canónica | Protocolo | Vistas |
|---|---|---|
| Emite eventos autorizados del workflow | HTTPS/Webhook | logica_expo_01 |
| Entrega eventos de ejecución para registrar contexto del pipeline | Azure Service Bus | logica_expo_01 |
| Entrega evidencia normalizada para registro y consulta | Azure Service Bus | logica_expo_01 |
| Persiste pipelines, etapas, estados y metadatos de ejecución | PostgreSQL | logica_expo_03 |
| Persiste y consulta metadatos y referencias de evidencia normalizada | PostgreSQL | logica_expo_03 |
| Almacena y resuelve referencias de logs extensos y evidencias | Object Storage API | logica_expo_03 |
| Persiste diagnóstico, recomendaciones y vínculos con evidencia | PostgreSQL | logica_expo_03 |
| Recupera logs, artefactos y metadatos autorizados | GitHub API/HTTPS | logica_expo_01 |
| Publica evidencia normalizada y protegida | Azure Service Bus | logica_expo_01 |
| Entrega eventos normalizados para procesamiento | Azure Service Bus | logica_expo_02 |
| Entrega logs y evidencia procesada para correlación | REST/HTTPS | logica_expo_02 |
| Recupera conocimiento operacional semánticamente relacionado | PostgreSQL/pgvector | logica_expo_02 |
| Proporciona repositorio, commits y definición de workflows CI/CD | GitHub API/HTTPS | logica_expo_01 |
| Proporciona telemetría y evidencia operacional autorizada | REST/HTTPS | logica_expo_01 |
| Consulta resultados y registra revisión humana | HTTPS | logica_expo_03 |
| Entrega contexto correlacionado del incidente para diagnóstico asistido | REST/HTTPS | logica_expo_02 |
| Solicita conocimiento contextual autorizado para el incidente | REST/HTTPS | logica_expo_02 |
| Solicita inferencia diagnóstica con evidencia saneada y contexto RAG | Azure OpenAI API/HTTPS | logica_expo_02 |
| Autentica usuarios corporativos | OIDC/OAuth2/HTTPS | logica_expo_03 |
| Consume APIs protegidas del prototipo | REST/HTTPS | logica_expo_03 |
| Enruta consultas de pipelines y ejecuciones | REST/HTTPS | logica_expo_03 |
| Enruta consultas de logs, eventos y evidencias | REST/HTTPS | logica_expo_03 |
| Enruta consultas y operaciones de diagnóstico y revisión | REST/HTTPS | logica_expo_03 |
| Persiste decisiones y trazabilidad de revisión humana | PostgreSQL | logica_expo_03 |
| Consulta diagnostic_output para publicar el artifact del workflow | REST/HTTPS | logica_expo_03 |

## Relaciones entre vistas

- `rel_correlation_postgresql`: Servicio de Correlación de Evidencias → PostgreSQL: Registra contexto correlacionado y trazabilidad (PostgreSQL).
