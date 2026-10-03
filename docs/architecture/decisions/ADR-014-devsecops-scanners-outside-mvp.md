Title: DevSecOps scanners outside direct MVP integrations
Status: Accepted
Date: 2026-10-03

## Decision

No direct Checkmarx/Mend/Wiz integrations in MVP.

GitHub Actions remains the integration boundary.
Scanner/quality-gate evidence may enter through workflow logs, events or artifacts.
Direct scanner APIs are future extensions.

Los quality gates se conservan como concepto del dominio. Cuando los análisis
participen en GitHub Actions, su evidencia podrá consumirse indirectamente por
los canales del workflow ya existentes. No se agregan nodos ni integraciones
directas con scanners; GitHub Actions sigue siendo la fuente principal de
logs, eventos y artifacts del pipeline.
