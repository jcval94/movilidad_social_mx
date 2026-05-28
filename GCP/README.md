# API GCP para Movilidad Social MX

Esta carpeta contiene una versión servible en Google Cloud Run de la inferencia probabilística usada por la aplicación de Movilidad Social MX. El objetivo es exponer un contrato HTTP estable para consumidores internos o externos sin acoplarlos a Streamlit.

## Estructura

```text
GCP/
  api/                 # Aplicación FastAPI y adaptador del modelo
  tests/               # Pruebas de contrato y servicio de modelo
  docs/                # Documentación técnica, operativa y de seguridad
  deploy/              # Manifiestos Cloud Run y Terraform
  examples/            # Payloads y comando curl listos para consumir
```

## Ejecución local

Desde la raíz del repositorio:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r GCP/requirements-api.txt
uvicorn GCP.api.main:app --reload --port 8080
```

La API asume por defecto que el artefacto existe en `models/modelo_entrenado.joblib`. Puedes cambiarlo con:

```bash
export MSMX_API_MODEL_PATH=/ruta/al/modelo.joblib
```

## Endpoints

- `GET /healthz`: liveness simple del proceso.
- `GET /readyz`: valida que el modelo pueda cargarse.
- `POST /v1/predict`: predice probabilidades por clase socioeconómica.

Consulta `docs/contrato_api.md` y `openapi.json` para el contrato completo.

## Variables de entorno principales

| Variable | Descripción | Default |
| --- | --- | --- |
| `MSMX_API_MODEL_PATH` | Ruta del artefacto `joblib` del modelo. | `models/modelo_entrenado.joblib` |
| `MSMX_API_ENVIRONMENT` | Ambiente lógico: `local`, `dev`, `staging` o `prod`. | `local` |
| `MSMX_API_CORS_ORIGINS` | Lista JSON/CSV de orígenes permitidos por CORS. | `[]` |
| `MSMX_API_LOG_LEVEL` | Nivel de logging esperado por el runtime. | `INFO` |

## Pruebas

```bash
pytest GCP/tests
```

## Despliegue

- `deploy/cloudrun.service.yaml` sirve como plantilla declarativa para Cloud Run.
- `deploy/terraform/` define recursos mínimos para habilitar Cloud Run con una imagen ya publicada en Artifact Registry.
- `Dockerfile` empaqueta sólo los artefactos necesarios para servir la API.
