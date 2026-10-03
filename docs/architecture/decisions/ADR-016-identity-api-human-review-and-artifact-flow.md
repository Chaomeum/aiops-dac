Title: Identity, API perimeter, human review and artifact flow
Status: Accepted
Date: 2026-10-03

## Decision

- Retirar el elemento activo `access_and_governance_controls` y conservar las menciones históricas en ADR anteriores.
- Representar Microsoft Entra ID con `entra_id` como proveedor corporativo externo de identidad, autenticación y emisión de tokens, sin host propio.
- Representar Azure API Management con `api_management` como contenedor de perímetro y enrutamiento API gestionado en Azure, con políticas de acceso. No se despliega en Azure Container Apps.
- Declarar `human_review_component` como componente interno de `recommendation_service`. Gestiona clasificación de riesgo, marcado de recomendaciones críticas, aprobación humana y registro, validación, corrección o rechazo de diagnósticos; no es otro microservicio.

El dashboard autentica usuarios con Entra ID mediante OIDC/OAuth2/HTTPS y consume las APIs protegidas mediante APIM (REST/HTTPS). APIM enruta a `pipeline_service`, `log_event_service` y `recommendation_service`. El flujo Human-in-the-Loop sigue usuarios → dashboard → APIM → recommendation_service → human_review_component → PostgreSQL, con comunicación interna `in-process` entre el servicio y su componente. Se mantienen los campos obligatorios de revisión: diagnostic_id, reviewer, decision, timestamp y correlationId, y el audit trail funcional en PostgreSQL.

GitHub Actions consulta `diagnostic_output` mediante APIM → recommendation_service y el propio workflow publica el artifact por un paso nativo (`workflow_pull_then_native_upload`). El GitHub App permanece read-only con installation tokens; el prototipo no escribe ni sube artifacts directamente a GitHub.

Los outputs diagnostic_hypothesis y github_actions_diagnostic_artifact son producidos por recommendation_service; el artifact es publicado por github_actions. dashboard_output es producido por web_dashboard.

Se corrige INV-009 para aplicar los 365 días ya aprobados en ADR-013, basados exclusivamente en política corporativa comunicada por el stakeholder. No se modifica la duración, el alcance ni la fuente de la política, ni se renumeran IDs históricos.

## Rationale

El antiguo elemento access_and_governance_controls mezclaba infraestructura de identidad, infraestructura API, gobierno transversal y lógica Human-in-the-Loop. Separar estas responsabilidades antes de construir C4 permite representar el consumo, la revisión humana y la publicación del artifact con fronteras y ownership explícitos.
