Title: Diagnostic service component boundaries
Status: Accepted
Date: 2026-10-03

## Decision

`recommendation_service`, denominado Diagnostic & Recommendation Service,
constituye el objeto de Zoom-In de C4 Level 3. Su descomposición interna aprobada es:

- Diagnostic API (`diagnostic_api_component`): recibe consultas diagnósticas,
  expone `diagnostic_output` y recibe operaciones de revisión humana.
- Diagnostic Orchestrator (`diagnostic_orchestrator_component`): coordina el
  contexto correlacionado y solicita contexto RAG e inferencia LLM, conforme a
  ADR-015.
- Diagnostic Output Composer (`diagnostic_output_component`): compone causa
  probable y recomendaciones, asocia evidencia y fuentes consultadas, y expone
  limitaciones y confianza del contrato `diagnostic_output`, conforme a ADR-009.
- Human Review & Diagnostic Governance (`human_review_component`): conserva
  sus responsabilidades y su parent `recommendation_service`, conforme a
  ADR-011 y ADR-016.

Los cuatro elementos son componentes internos del mismo
`recommendation_service`. Esta decisión no crea nuevos microservicios ni nuevos
containers, ni agrega capacidades ajenas a `diagnostic_output` y a las
responsabilidades existentes del servicio.

Las relaciones de componentes proyectan internamente las relaciones canónicas
del servicio y se utilizan solamente en C4 Level 3. No sustituyen ni eliminan
relaciones entre containers. Se conserva `rel_human_review_postgresql`.

## Rationale

Hacer explícitos los límites internos del servicio para el Zoom-In C4, conservando
las fronteras de runtime y orquestación de ADR-015 y el flujo de acceso, revisión
humana y persistencia de ADR-016.
