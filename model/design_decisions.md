# Decisiones propuestas del diseño de clases

SSOT exclusivo: `model/design.yml`, versión 1.0.0. Todas las clases son
`proposed`: este repositorio DaC no contiene el microservicio Java/Spring Boot.
Estas decisiones concretan clases dentro de las fronteras ya aprobadas; no
modifican ADR-018 ni resuelven preguntas del dominio.

## DC-001 — Controllers separados para commands y queries

`DiagnosisCommandController` y `DiagnosisQueryController` delegan a contratos
de aplicación distintos. Human Review usa la misma separación con sus dos
controllers. Los controllers pertenecen a `diagnostic_api_component`, incluso
cuando se muestran como entrada al zoom de Human Review. No contienen reglas
de dominio; sus firmas abrevian los datos REST, sin introducir rutas nuevas.
Los commands devuelven UUID; las queries solo leen y componen resultados.

## DC-002 — Puertos de aplicación para RAG y LLM

`KnowledgeRetrievalPort` y `DiagnosticLlmGateway` son interfaces de salida.
El orquestador depende de ellas; los adaptadores HTTP las implementan en
infraestructura. El gateway acepta únicamente `SanitizedDiagnosticContext`,
con las tres partes del contrato LLM vigente. La traducción RAG ocurre dentro
de su adaptador y conserva provenance; ninguna respuesta externa alcanza el
dominio con tipos de proveedor.

## DC-003 — ACL de respuesta Azure OpenAI

`LlmResponseTranslator`, en `infrastructure.acl`, convierte la respuesta Azure
en `Diagnosis` y sus recomendaciones internas. El gateway devuelve este
resultado interno, todavía sin persistir. `DiagnosticOutputComposer` asocia
contexto, evidencia y fuentes; el repositorio inserta el snapshot y sus vínculos.
Los tipos de SDK/HTTP/JSON de proveedor quedan dentro de infraestructura.

## DC-004 — DiagnosticView como proyección de aplicación

`DiagnosticView` expresa el read model de `diagnostic_output`, con sus campos
canónicos. Usa el estereotipo permitido `ValueObject` y `role: read_model`;
no es un Aggregate ni una entidad persistida. Las queries usan exclusivamente
métodos de lectura de los repositorios existentes. La proyección se compone
en aplicación, sin SQL views ni nuevas tablas. `DiagnosticApiMapper` se omite
porque no añade semántica al zoom; la adaptación simple queda en el controller.

## DC-005 — AuditTrailPort transversal con metadata mínima

`AuditTrailPort` aísla el mecanismo técnico de registro de revisión humana.
`PostgresAuditTrailAdapter` escribe en `audit.audit_events`, mediante la
excepción transversal ya documentada por ADR-011/DD-016. Su operación recibe
solo IDs, actor, decisión, tiempo y correlación; excluye comentario, causa,
evidencia y contenido sensible. No constituye un nuevo Bounded Context.

## DC-006 — Repositorios de dominio sin dependencia JPA

`DiagnosisRepository` y `HumanReviewRepository` son interfaces en
`domain.services`. Sus adaptadores viven en `infrastructure.persistence.jpa`.
`ProbableCause` envuelve exclusivamente el texto existente. Las asociaciones
del Aggregate se representan por relaciones de composición, sin añadir
atributos persistidos a las columnas de `domain.yml`. Los IDs entre contextos
no se convierten en asociaciones ORM. HumanReview valida la decisión sin
reescribir el snapshot diagnóstico original.

Las assumptions DA-001 a DA-006 están en el SSOT. DQ-002 se referencia sin
resolverla; DCQ-001/DCQ-002 dejan abiertas la política concreta de riesgo y
la forma final del contrato REST de recepción. DCQ-003 conserva abierta la
rehidratación del contexto operacional al consultar el read model; no elige
almacenamiento ni una comunicación nueva. Las restantes preguntas de
`domain.yml` siguen intactas. Ninguna de estas decisiones necesita una nueva
decisión arquitectónica para generar las figuras propuestas.
