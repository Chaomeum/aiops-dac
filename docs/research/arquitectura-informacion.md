Sí. Tomando únicamente lo que ya cerramos en la arquitectura de información, este sería el extracto útil para pasar al modelado funcional y luego a base de datos/API.

## 1. Pantallas y datos mostrados

| Pantalla | Datos principales |
|---|---|
| **Operations** | Resumen de incidentes activos; `incident_id`; severidad; repositorio; workflow; etapa; diagnóstico resumido; estado del diagnóstico; estado operacional; assignee; tiempo transcurrido. Filtros por severidad, repositorio, etapa, estado y assignee. Scope `Mine / Unassigned / All`. |
| **Operations — Needs validation** | Incidentes ya resueltos cuyo diagnóstico todavía requiere confirmación humana; incidente, pipeline, diagnóstico propuesto, assignee, fecha/hora de resolución y estado de validación. |
| **Incident Workspace — Open / Diagnosis ready** | `incident_id`; repositorio; workflow; run; branch; commit; stage; severity; incident status; assignee; causa probable; confidence; explicación; evidencias correlacionadas; fragmentos de logs/eventos; recomendación; PR/commit/run relacionados; timestamps del incidente. |
| **Incident Workspace — Verification** | Todo el contexto anterior más run de verificación, resultado del run, tiempos de remediación/verificación y timeline actualizado. |
| **Incident Workspace — Resolved / Validation** | Resultado final del incidente; tiempo de diagnóstico; tiempo de resolución; run exitoso/final; diagnóstico original; validación `Confirmed / Rejected`; comentario o causa real cuando corresponda. |
| **History — Incidents** | Incidentes resueltos; pipeline; stage; diagnóstico registrado; validation outcome; assignee; diagnosis time; resolution time; fecha de resolución. |
| **History — Insights** | Mean diagnosis time; MTTR; diagnosis confirmation rate; resolved incidents; evolución temporal del diagnosis time; incidentes por stage; confirmed/rejected; concentración o recurrencia por pipeline + stage. |
| **Pipelines** | Workflow monitorizado; repositorio; environment; criticality; responsible team; monitoring status. |
| **Pipeline Detail** | Repositorio; workflow; environment; default branch; integración GitHub Actions; criticality; monitoring; responsible team; pipeline owners; capacidades de acceso; último cambio de configuración y auditoría básica. |
| **Add monitored workflow** | Repositorio; workflow; environment; criticality; responsible team; owners; estado inicial de monitoring. |

Los valores de dominio que ya hemos cerrado son:

```text
IncidentStatus
OPEN
IN_REMEDIATION
VERIFICATION
RESOLVED

DiagnosisStatus
ANALYZING
DIAGNOSIS_READY
INCONCLUSIVE

ValidationStatus
PENDING
CONFIRMED
REJECTED

Severity / Criticality
CRITICAL
HIGH
MEDIUM
LOW

PipelineStage
BUILD
TESTING
QUALITY_GATE
DEPLOYMENT
CONTAINER
INFRASTRUCTURE

MonitoringStatus
ACTIVE
PAUSED

AccessCapability
VIEW
OPERATE
CONFIGURE
```

La escala de severidad operacional del incidente debe mantenerse separada de niveles de log como `INFO`, `WARNING`, `ERROR`, `SEVERE` o `DEBUG`.

---

## 2. Acciones del usuario

| Contexto | Acción |
|---|---|
| Operations | Buscar incidentes |
| Operations | Filtrar por severity, repository, stage, status, assignee |
| Operations | Cambiar scope entre `Mine`, `Unassigned`, `All` |
| Operations | Abrir Incident Workspace |
| Operations | `Assign to me` para un incidente no asignado |
| Incident Workspace | Cambiar assignee, si tiene autorización |
| Incident Workspace | Expandir evidencia mediante `View context` |
| Incident Workspace | Consultar `View full event timeline` |
| Incident Workspace | Abrir run, commit o pull request en GitHub |
| Incident Workspace | `Start remediation` |
| Verification | Abrir verification run en GitHub |
| Verification | `Resolve incident` |
| Validation | `Confirm diagnosis` |
| Validation | `Reject diagnosis` |
| Validation | Registrar causa real/comentario cuando el diagnóstico se rechaza |
| History | Buscar y filtrar incidentes históricos |
| History | Abrir Incident Workspace histórico |
| Insights | Filtrar por periodo, repository, pipeline, stage y severity |
| Pipelines | Buscar/filtrar workflows monitorizados |
| Pipelines | Abrir Pipeline Detail |
| Pipelines | `Add monitored workflow` |
| Pipeline Detail | Cambiar Criticality |
| Pipeline Detail | Activar/pausar Monitoring |
| Pipeline Detail | `Edit ownership` |
| Pipeline Detail | Administrar capacidades `View / Operate / Configure` |
| Pipeline Detail | Abrir repository/workflow en GitHub |
| Pipeline Detail | Consultar configuration history |

No forman parte del flujo acordado acciones como `Apply fix`, `Auto-remediate`, modificación de YAML, manejo de secretos o edición de permisos de GitHub.

---

# 3. REST API propuesta a partir de la IA

Esto **no proviene literalmente del Charter**. Es un contrato API v0.1 derivado de las vistas y flujos que ya definimos, por lo que puede servirnos como base para el diseño backend.

### Incidents

| Método | Endpoint | Uso |
|---|---|---|
| `GET` | `/api/incidents` | Incident Queue |
| `GET` | `/api/incidents/{incidentId}` | Incident Workspace |
| `PATCH` | `/api/incidents/{incidentId}/assignee` | Asignar/reasignar |
| `POST` | `/api/incidents/{incidentId}/remediation` | Registrar `Start remediation` |
| `POST` | `/api/incidents/{incidentId}/resolve` | Resolver incidente |
| `POST` | `/api/incidents/{incidentId}/validation` | Confirmar/rechazar diagnóstico |
| `GET` | `/api/incidents/{incidentId}/evidence` | Evidencia correlacionada |
| `GET` | `/api/incidents/{incidentId}/timeline` | Timeline completo |
| `GET` | `/api/incidents/{incidentId}/runs` | Runs relacionados / verification |

Ejemplo:

```http
GET /api/incidents?scope=mine&status=OPEN,IN_REMEDIATION,VERIFICATION&severity=CRITICAL,HIGH&repositoryId=...&stage=DEPLOYMENT&assigneeId=...&q=...
```

### History / Insights

| Método | Endpoint | Uso |
|---|---|---|
| `GET` | `/api/incidents/history` | Tabla histórica |
| `GET` | `/api/insights/incidents` | KPIs y agregados |
| `GET` | `/api/insights/diagnosis-time` | Evolución de diagnosis time |
| `GET` | `/api/insights/incidents-by-stage` | Distribución por stage |
| `GET` | `/api/insights/diagnosis-outcomes` | Confirmed vs Rejected |
| `GET` | `/api/insights/repeated-contexts` | Agrupación pipeline + stage |

Todos podrían aceptar:

```text
from
to
repositoryId
pipelineId
stage
severity
```

### Pipelines

| Método | Endpoint | Uso |
|---|---|---|
| `GET` | `/api/pipelines` | Inventario monitorizado |
| `POST` | `/api/pipelines` | Add monitored workflow |
| `GET` | `/api/pipelines/{pipelineId}` | Pipeline Detail |
| `PATCH` | `/api/pipelines/{pipelineId}/policy` | Criticality |
| `PATCH` | `/api/pipelines/{pipelineId}/monitoring` | Active / Paused |
| `PATCH` | `/api/pipelines/{pipelineId}/ownership` | Team y owners |
| `PUT` | `/api/pipelines/{pipelineId}/access` | View / Operate / Configure |
| `GET` | `/api/pipelines/{pipelineId}/configuration-history` | Auditoría de configuración |

La exploración de repositorios/workflows de GitHub para `Add monitored workflow` todavía no quedó cerrada técnicamente. Si finalmente el backend la ofrece, podrían existir endpoints del tipo:

```text
GET /api/integrations/github/repositories
GET /api/integrations/github/repositories/{repositoryId}/workflows
```

pero estos los dejaría **provisionales** hasta diseñar formalmente la integración GitHub.

---

# 4. Campos principales de respuesta

## Incident summary

Para Operations:

```json
{
  "id": "INC-1039",
  "severity": "HIGH",
  "status": "OPEN",
  "diagnosisStatus": "DIAGNOSIS_READY",
  "validationStatus": "PENDING",

  "repository": {
    "id": "repo-id",
    "name": "acme/web-storefront"
  },

  "pipeline": {
    "id": "pipeline-id",
    "workflowName": "Build and test"
  },

  "stage": "BUILD",

  "diagnosis": {
    "summary": "Dependency version mismatch",
    "confidence": 0.88
  },

  "assignee": {
    "id": "user-id",
    "displayName": "Maya Patel"
  },

  "detectedAt": "...",
  "elapsedSeconds": 11160
}
```

No asumiría todavía que `confidence` necesariamente será un `float 0–1` en persistencia; eso lo podemos decidir durante el modelamiento. El ejemplo solamente representa el contrato conceptual.

---

## Incident detail

```json
{
  "id": "INC-1039",

  "severity": "HIGH",
  "status": "OPEN",
  "diagnosisStatus": "DIAGNOSIS_READY",
  "validationStatus": "PENDING",

  "repository": {},
  "pipeline": {},

  "run": {
    "id": "1842",
    "branch": "main",
    "commitSha": "a85c2f1"
  },

  "stage": "BUILD",

  "diagnosis": {
    "summary": "Dependency version mismatch",
    "explanation": "...",
    "confidence": 0.88
  },

  "recommendation": {
    "description": "...",
    "relatedPullRequest": "418"
  },

  "ownership": {
    "responsibleTeam": {},
    "assignee": {}
  },

  "timing": {
    "detectedAt": "...",
    "diagnosisReadyAt": "...",
    "remediationStartedAt": null,
    "verificationStartedAt": null,
    "resolvedAt": null,
    "diagnosisTimeSeconds": 131,
    "elapsedSeconds": 11160
  }
}
```

---

## Evidence

```json
{
  "id": "evidence-id",
  "incidentId": "INC-1039",
  "observedAt": "...",
  "source": "GITHUB_ACTIONS",
  "stage": "BUILD",
  "job": "Install dependencies",
  "summary": "Dependency installation could not resolve the package tree",
  "excerpt": "npm ERR! ERESOLVE unable to resolve dependency tree",
  "sequence": 2
}
```

El contexto ampliado podría recuperarse mediante:

```http
GET /api/incidents/{incidentId}/evidence/{evidenceId}
```

o formar parte del mismo DTO posteriormente.

---

## Validation

Request:

```json
{
  "result": "REJECTED",
  "actualCause": "Incorrect environment configuration",
  "comment": "The dependency warning was unrelated to the final failure."
}
```

o:

```json
{
  "result": "CONFIRMED"
}
```

Además deberían registrarse internamente:

```text
validatedBy
validatedAt
```

---

## Pipeline

```json
{
  "id": "pipeline-id",

  "repository": {
    "id": "repo-id",
    "name": "acme/payments-api"
  },

  "workflow": {
    "externalId": "...",
    "name": "deploy-production",
    "file": "deploy-production.yml"
  },

  "environment": "Production",
  "defaultBranch": "main",

  "criticality": "CRITICAL",
  "monitoringStatus": "ACTIVE",

  "responsibleTeam": {
    "id": "team-id",
    "name": "Platform Engineering"
  },

  "owners": [],

  "integration": {
    "provider": "GITHUB_ACTIONS",
    "status": "CONNECTED"
  }
}
```

---

## Insights

Podría devolverse incluso como un único agregado:

```json
{
  "summary": {
    "meanDiagnosisTimeSeconds": 138,
    "mttrSeconds": 872,
    "diagnosisConfirmationRate": 0.84,
    "resolvedIncidents": 43
  },

  "diagnosisTimeTrend": [],

  "incidentsByStage": [],

  "diagnosisOutcomes": {
    "confirmed": 36,
    "rejected": 7
  },

  "repeatedContexts": []
}
```

Para una implementación más desacoplada, estas métricas pueden tener endpoints independientes; eso lo resolveremos cuando diseñemos el backend.

---

## 5. Cosas que todavía NO daría por cerradas para base de datos

Antes de pasar de esto a entidades/tablas físicas tenemos que resolver varias decisiones que la IA visual no determina por sí sola:

**Relación Incident–PipelineRun.** Tenemos claro que el Incident es la entidad principal, pero debemos decidir formalmente si un incidente nace de exactamente un failed run y después referencia varios verification runs, o si puede agrupar varios fallos relacionados desde el inicio.

**Modelo Repository–Workflow–Pipeline.** Debemos decidir si `Pipeline` representa directamente un GitHub Workflow monitorizado o si conviene separar `Repository`, `Workflow` y `MonitoredPipeline`.

**Evidence.** Debemos definir cuánto persistimos realmente: fragmento normalizado, referencia al log original, hash, ubicación externa, metadata, etc.

**Diagnosis.** Debemos decidir si existe un único diagnóstico actual por incidente o un historial versionado de hipótesis.

**Recommendation.** Puede ser parte de `Diagnosis` o una entidad propia si queremos historial/auditoría.

**Assignee vs ownership.** Son conceptos diferentes y deben quedar separados en el modelo.

**Teams / roles / capabilities.** Sabemos que necesitamos `View / Operate / Configure`, pero todavía no está cerrada la implementación RBAC ni los nombres definitivos de roles.

**Severity derivation.** Tenemos el concepto `Pipeline Criticality + incident context`, pero todavía no la regla concreta.

**Taxonomía RCA.** Deliberadamente no la hemos cerrado, por lo que no crearía todavía una tabla rígida `failure_type` con categorías inventadas.

Este es exactamente el material que yo usaría como **entrada funcional para la siguiente fase de modelado entidad–relación**, pero todavía no como esquema SQL definitivo.