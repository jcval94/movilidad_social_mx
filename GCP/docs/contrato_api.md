# Contrato de API

## Base URL

Local:

```text
http://localhost:8080
```

Cloud Run:

```text
https://<servicio>-<hash>-<region>.run.app
```

## `GET /healthz`

Verifica que el proceso HTTP está vivo.

### Respuesta `200`

```json
{
  "status": "ok",
  "service": "Movilidad Social MX API",
  "version": "0.1.0",
  "environment": "prod"
}
```

## `GET /readyz`

Carga o reutiliza el modelo y confirma que puede atender inferencia.

### Respuesta `200`

```json
{
  "status": "ready",
  "model_version": "modelo_entrenado.joblib",
  "features": 9
}
```

### Respuesta `503`

```json
{
  "error": "model_not_ready",
  "detail": "No se encontró el modelo en models/modelo_entrenado.joblib."
}
```

## `POST /v1/predict`

Predice clase socioeconómica probabilística.

### Request

```json
{
  "request_id": "demo-001",
  "features": {
    "p126d": 1,
    "p131": 0,
    "p125d": 1,
    "p126f": 0,
    "p126g": 0,
    "p125e": 0,
    "p129a": 0,
    "p125a": 1,
    "p126b": 1
  }
}
```

### Semántica de features

- Las variables deben coincidir con columnas conocidas por el modelo.
- Las variables omitidas se completan con `0`.
- Las variables extra se rechazan con `422` para evitar inferencias silenciosamente incorrectas.

### Respuesta `200`

```json
{
  "request_id": "demo-001",
  "predicted_class": 3,
  "predicted_label": "Media Baja",
  "predicted_probability": 0.42,
  "probabilities": [
    {"class_id": 1, "label": "Baja Baja", "probability": 0.10},
    {"class_id": 2, "label": "Baja Alta", "probability": 0.20},
    {"class_id": 3, "label": "Media Baja", "probability": 0.42},
    {"class_id": 4, "label": "Media Alta", "probability": 0.18},
    {"class_id": 5, "label": "Alta", "probability": 0.10}
  ],
  "model_version": "modelo_entrenado.joblib",
  "feature_order": ["p126d", "p131", "p125d", "p126f", "p126g", "p125e", "p129a", "p125a", "p126b"]
}
```

## Errores

| Código | `error` | Causa típica |
| --- | --- | --- |
| `422` | `validation_error` | JSON con forma inválida o campos no permitidos. |
| `422` | `invalid_features` | Variables desconocidas por el modelo. |
| `503` | `model_not_ready` | Artefacto ausente o estimador incompatible. |
