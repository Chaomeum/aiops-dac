Title: Diagnostic runtime boundaries and orchestration
Status: Accepted
Date: 2026-10-03

## Decision

- `nlp_log_processor` y `rag_retrieval` son contenedores propios desplegados en Microsoft Azure, con runtime controlado y Azure Container Apps. Se conservan Drain3 y Azure OpenAI Embeddings.
- `rag_retrieval` se limita a recuperación de conocimiento autorizado, búsqueda semántica, conservación de provenance e interacción con `pgvector_knowledge_store`.
- Se mantiene el ID `pretrained_llm_diagnostic_service`, que representa Azure OpenAI Service como sistema externo gestionado, integrado mediante `service_api`. La familia es GPT-4 y el modelo concreto permanece sin fijar (`null`). El proyecto no ejecuta ni aloja el modelo; no tiene host propio ni despliegue en Azure Container Apps.
- `recommendation_service`, con nombre visible Diagnostic & Recommendation Service, es propietario de la orquestación de diagnóstico asistido. Mantiene sus responsabilidades de recomendaciones y `diagnostic_output`, y persiste diagnóstico, recomendaciones y vínculos con evidencia en PostgreSQL.

El flujo canónico entrega contexto correlacionado desde `evidence_correlation_engine` a `recommendation_service`. Este solicita conocimiento contextual a `rag_retrieval`, que consulta `pgvector_knowledge_store`; después solicita inferencia a Azure OpenAI con evidencia saneada y contexto RAG. Las llamadas son síncronas: REST/HTTPS para el backend y Azure OpenAI API/HTTPS para la inferencia. La respuesta de Azure OpenAI vuelve por la misma llamada, sin una relación separada de respuesta HTTP.

## Rationale

Separar fronteras de ejecución y explicitar la propiedad del flujo RAG/LLM antes de construir C4 y DBML. La recuperación RAG conserva su responsabilidad especializada y el prototipo integra un modelo preentrenado mediante API.
