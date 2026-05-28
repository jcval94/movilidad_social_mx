# Operación

## Señales de salud

- `/healthz`: indica que el proceso FastAPI responde.
- `/readyz`: indica que el modelo existe, se cargó y expone `predict_proba`.

## Métricas recomendadas

En Cloud Run, monitorear:

- Latencia p50/p95/p99 de `POST /v1/predict`.
- Tasa de respuestas `4xx` y `5xx`.
- Instancias activas y cold starts.
- Uso de memoria durante carga del modelo.

## Logs

Cloud Run captura stdout/stderr automáticamente. Se recomienda incluir en la capa de plataforma:

- `request_id` enviado por consumidor cuando exista.
- Código de estado HTTP.
- Latencia total por request.
- Versión de imagen desplegada.

No se deben registrar payloads completos si contienen datos sensibles o identificables.

## Runbook básico

### `/readyz` devuelve `503`

1. Verificar `MSMX_API_MODEL_PATH`.
2. Confirmar que el archivo existe dentro de la imagen o volumen.
3. Confirmar que el estimador implementa `predict_proba`.
4. Revisar logs de arranque y permisos de lectura.

### Aumentan los `422`

1. Revisar si consumidores envían variables nuevas o mal escritas.
2. Comparar contra `feature_order` devuelto por una respuesta válida.
3. Actualizar documentación si hubo un cambio legítimo de modelo.

### Latencia alta

1. Revisar memoria asignada y CPU de Cloud Run.
2. Confirmar que no hay carga repetida del modelo por request.
3. Aumentar `min_instance_count` si cold starts afectan la experiencia.
