FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    MSMX_API_ENVIRONMENT=prod \
    MSMX_API_MODEL_PATH=models/modelo_entrenado.joblib

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY GCP/requirements-api.txt /app/GCP/requirements-api.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/GCP/requirements-api.txt

COPY GCP/api /app/GCP/api
COPY GCP/openapi.json /app/GCP/openapi.json
COPY models/modelo_entrenado.joblib /app/models/modelo_entrenado.joblib

USER app

EXPOSE 8080

CMD ["sh", "-c", "uvicorn GCP.api.main:app --host 0.0.0.0 --port ${PORT}"]
