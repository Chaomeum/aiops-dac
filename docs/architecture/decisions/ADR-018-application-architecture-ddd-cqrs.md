Title: Application architecture with microservices, DDD and logical CQRS
Status: Accepted
Date: 2026-10-03

## Context

El equipo ha aprobado la arquitectura de aplicación para los contenedores
existentes. Esta decisión concreta tecnologías y organización de aplicación;
conserva las fronteras C4, las relaciones, las integraciones y los invariantes
del modelo vigente. La autoridad se aplica por materia: el Project Charter
delimita alcance; INV-*, ADR Accepted y `architecture.yml` rigen la arquitectura;
`tech_drift_resolutions` y los ADR tecnológicos rigen tecnología. La arquitectura
de información deriva necesidades funcionales dentro de esos límites.

## Decision

- Microservicios y **multirepo**: cada microservicio desplegable tiene un
  repositorio/proyecto independiente. No se diseña un monorepo multimódulo.
- Java y Spring Boot para `ingestion_normalization_service`, `pipeline_service`,
  `log_event_service`, `evidence_correlation_engine` y `recommendation_service`.
- Python y FastAPI para `nlp_log_processor` y `rag_retrieval`.
- React y TypeScript para `web_dashboard`, conservando SPA y Azure Static Web Apps.
- DDD táctico donde exista dominio significativo. Entidades, Value Objects y
  Aggregates deben responder a invariantes reales. DDD no obliga a introducir
  Aggregates artificiales en todos los servicios. `ingestion_normalization_service`
  y `nlp_log_processor` pueden tener un modelo ligero por su carácter técnico.
- CQRS lógico en la capa de aplicación:

  ```text
  Command → Command Service / Handler → Domain → Repository → PostgreSQL
  Query → Query Service / Handler → Query Repository / Projection → PostgreSQL
  ```

  Una proyección de consulta puede componerse en aplicación; esta iteración no
  define SQL views. No hay Event Sourcing, Event Store ni bases físicas distintas
  para escritura y lectura. La mensajería existente y la auditoría funcional no
  constituyen un Event Store.
- Una sola instancia física PostgreSQL. Los schemas `ops`, `evidence`,
  `diagnosis`, `knowledge` y `audit` delimitan ownership de datos.
- `pipeline_service` posee `ops`; `log_event_service` posee `evidence_items` y
  `evidence_correlation_engine` posee `correlated_contexts` dentro de `evidence`;
  `recommendation_service` posee `diagnosis`; `rag_retrieval` posee `knowledge`.
  `audit` pertenece a la capacidad transversal compartida, sin crear audit_service.
  Cada servicio escribe exclusivamente sus tablas. Compartir schema no autoriza
  a modificar tablas del otro servicio.
- Se permiten FK físicas dentro de un schema. Entre schemas se usan IDs lógicos,
  sin FK PostgreSQL. La comunicación sigue las APIs/eventos declarados en
  `architecture.yml`; no se agregan relaciones para resolver la persistencia.
- No hay asociaciones JPA navegables ni navegación ORM entre contextos; se
  conservan IDs y se resuelve el contexto por los contratos existentes.

## Consequences and reversibility

El modelo persistente se mantiene en `model/domain.yml`; DBML, SQL, un ER y el
diccionario se derivan determinísticamente. Las nuevas decisiones físicas se
registran en `model/domain_decisions.md`, sin ampliar alcance ni resolver
preguntas abiertas. El diagnóstico sigue siendo causa probable y la remediación
permanece bajo control humano.

La ausencia de FK cross-schema es reversible mediante una futura decisión
Accepted y migraciones explícitas. Los owners validan referencias lógicas por
los contratos existentes; esta decisión no elige un mecanismo adicional de
consistencia distribuida ni otorga acceso de escritura entre contextos. Cambiar
stack, estrategia de repositorios o separación física también requiere una
decisión posterior. Se conserva la retención de 365 días de ADR-013 para logs,
diagnósticos y evidencias, sin implementar tareas de purga.
