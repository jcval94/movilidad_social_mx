# Checklist: Paper Trading -> Live Trading (futuro)

## Rendimiento en paper
- [ ] Ventana mínima de paper trading completada (definir N semanas).
- [ ] Error de tracking vs expectativa dentro de umbral.
- [ ] Incidentes críticos = 0 en ventana de evaluación.
- [ ] Drift monitorizado con decisiones documentadas.

## Riesgo y controles
- [ ] Límites de exposición y cash management validados.
- [ ] Kill switch definido y probado.
- [ ] Gestión de incidentes y on-call definida.
- [ ] Límites por ticker/estrategia acordados por riesgo.

## Integración broker (cuando exista)
- [ ] Adapter de broker real implementado con feature flag.
- [ ] Pruebas de sandbox del broker aprobadas.
- [ ] Idempotencia y deduplicación de órdenes validadas en integración.
- [ ] Reconciliación broker vs sistema interna aprobada.

## Compliance y seguridad
- [ ] Revisión de secretos, credenciales y rotación completada.
- [ ] Permisos mínimos (least privilege) aplicados.
- [ ] Auditoría de logs y trazabilidad completa.

## Go-live gradual
- [ ] Rollout escalonado (capital limitado / pocas estrategias).
- [ ] Umbrales de rollback automatizados.
- [ ] Runbook de operación y fallback aprobado.
- [ ] Aprobación final de comité técnico/riesgo.
