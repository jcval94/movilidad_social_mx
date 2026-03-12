# Checklist: Investigación -> Paper Trading

## Señales y modelo
- [ ] Hipótesis de investigación documentada.
- [ ] Métricas out-of-sample aceptables y estables.
- [ ] Test de no leakage aprobado.
- [ ] Configs validadas y sin supuestos implícitos.

## Backtest y ejecución simulada
- [ ] Backtests por estrategia y portfolio multiestrategia aprobados.
- [ ] Champion/challenger con criterio de aceptación definido.
- [ ] Costos explícitos (comisiones/slippage/fees) validados.
- [ ] Session gating e idempotencia de workflows probados.
- [ ] Reconciliación señal -> orden -> fill sin inconsistencias críticas.

## Observabilidad
- [ ] Notificaciones OPEN/OPEN+2H/OPEN+4H/OPEN+6H/CLOSE configuradas.
- [ ] Alertas de drift/retrain/incidentes habilitadas.
- [ ] Reportes diarios/semanales y model health habilitados.

## Datos y trazabilidad
- [ ] Snapshots versionados por fecha/sesión.
- [ ] Evitar duplicados validado.
- [ ] Exportación a Pages (latest + histórico) validada.
- [ ] Revisión de secretos y permisos aprobada.

## Aprobación
- [ ] Dueño cuantitativo aprueba.
- [ ] Dueño de plataforma aprueba.
- [ ] Go-live a paper trading aprobado con fecha.
