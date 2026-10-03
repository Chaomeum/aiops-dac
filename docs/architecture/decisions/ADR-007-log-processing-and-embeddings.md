Title: Log processing and embeddings for semantic retrieval
Status: Accepted
Date: 2026-10-03

## Decision

- Usar Drain3 para parsing y estructuración de logs.
- Usar Azure OpenAI Embeddings para recuperación semántica/RAG, sin fijar aún un modelo concreto.
- LogBERT permanece como candidato no confirmado; OQ-001 sigue abierta y la tecnología del detector permanece sin seleccionar.
- Los embeddings no forman parte de la entrada contractual del detector AIOps ni establecen una dependencia Azure OpenAI Embeddings -> LogBERT.

## Rationale

- Separar parsing, detección de anomalías y recuperación semántica.
- Evitar una dependencia no sustentada Azure OpenAI Embeddings -> LogBERT.
- Mantener el aporte de la tesis en integración, correlación, RAG y diagnóstico asistido.
