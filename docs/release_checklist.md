# Release Checklist Interna (Streamlit)

## Calidad técnica (obligatorio)
- [ ] Linting en verde (`ruff check .`).
- [ ] Unit tests en verde (`pytest -q`).
- [ ] Verificación rápida de imports (`python -m py_compile app.py section1.py section2.py section3.py section4.py data_utils.py config.py async_jobs.py diagnosis_worker.py session_manager.py state_backend.py llm/gemini_explainer.py`).
- [ ] La app inicia sin errores (`streamlit run app.py --server.headless true`).

## Datos y operación
- [ ] Archivos requeridos de `data/` presentes.
- [ ] Modelo en `models/modelo_entrenado.joblib` presente.
- [ ] Revisión de secretos accidentalmente versionados.
- [ ] Confirmar que no se exponen datos sensibles en tablas/exportaciones.

## Trazabilidad
- [ ] Changelog interno actualizado.
- [ ] PR con contexto de riesgos y rollback.
- [ ] Commit firmado/validado según política interna (si aplica).

## Aprobación final
- [ ] Validación de producto/negocio.
- [ ] Go/No-Go explícito con responsable.
- [ ] Tag de release creado.
