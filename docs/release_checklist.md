# Release Checklist Interna

## Calidad técnica (obligatorio)
- [ ] Linting en verde (`ruff check src tests scripts`).
- [ ] Type checking en verde (`mypy src/backtest src/execution src/notifications src/reporting src/storage scripts/validate_repo.py`).
- [ ] Unit tests en verde (`pytest -q`).
- [ ] Smoke tests end-to-end en verde (`python scripts/validate_repo.py --smoke`).
- [ ] Cobertura mínima razonable alcanzada (>= 65% en CI).
- [ ] Validación estricta de repo en verde (`python scripts/validate_repo.py --strict`).

## Seguridad y operación
- [ ] Revisión de secretos accidentalmente versionados.
- [ ] Verificación de permisos inseguros (archivos world-writable).
- [ ] Validación de schemas de datasets de exportación para Pages.
- [ ] Confirmar que no se exponen datos sensibles en exportación estática.

## Trazabilidad
- [ ] Changelog interno actualizado.
- [ ] PR con contexto de riesgos y rollback.
- [ ] Commit firmado/validado según política interna (si aplica).

## Aprobación final
- [ ] Validación de producto/negocio.
- [ ] Go/No-Go explícito con responsable.
- [ ] Tag de release creado.
