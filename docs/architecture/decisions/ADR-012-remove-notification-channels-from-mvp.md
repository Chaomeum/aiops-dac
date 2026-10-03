Title: Remove notification channels from MVP
Status: Accepted
Date: 2026-10-03

## Decision

Remove `optional_notification_channels` from MVP, sin crear un nodo sustituto.

El consumo operativo del MVP se limita al dashboard web y al artefacto diagnóstico
asociado a GitHub Actions. Teams, Slack y correo quedan únicamente como posibles
extensiones futuras. Las menciones históricas en documentos y ADRs se conservan.

## Rationale

- El Project Charter v1.3 establece dashboard web y reporte/artifact como mecanismos de consumo.
- Las notificaciones no aportan capacidad diagnóstica al core.
- Introducirían integraciones, credenciales y permisos adicionales.
- Teams/Slack/email pueden evaluarse posteriormente como extensiones.
