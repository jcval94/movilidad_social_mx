# Arquitectura de la API

## Propósito

La API separa la experiencia interactiva de Streamlit del consumo programático del modelo. El servicio recibe variables codificadas, alinea el orden de columnas esperado por el estimador y devuelve probabilidades por clase.

## Componentes

1. **FastAPI (`GCP/api/main.py`)**: define rutas HTTP, documentación OpenAPI y handlers de operación.
2. **Schemas (`GCP/api/schemas.py`)**: contratos Pydantic para validar entrada y salida.
3. **ModelService (`GCP/api/model_service.py`)**: adaptador hacia el artefacto `joblib`, con carga lazy y normalización de respuesta.
4. **Settings (`GCP/api/settings.py`)**: configuración por variables de entorno con prefijo `MSMX_API_`.
5. **Cloud Run**: runtime serverless recomendado para escalar a cero y aislar la API de la app Streamlit.

## Flujo de inferencia

```text
Consumidor HTTP
  -> POST /v1/predict
  -> Validación Pydantic
  -> ModelService.load() si el modelo aún no está cacheado
  -> Alineación de features al orden feature_names_in_
  -> predict_proba
  -> Respuesta JSON con clase predicha y vector de probabilidades
```

## Fuente de verdad del modelo

El artefacto por defecto es `models/modelo_entrenado.joblib`, el mismo modelo de clasificación utilizado por la sección de predicción socioeconómica de la aplicación principal. La API no reentrena modelos ni modifica datos.

## Decisiones de diseño

- **Carga lazy**: reduce fallos durante importación y permite que `/readyz` sea el punto explícito de verificación.
- **Contrato estricto**: se rechazan campos top-level no documentados y variables desconocidas del modelo.
- **Ceros para variables omitidas**: mantiene compatibilidad con formularios parciales donde las opciones no marcadas equivalen a `0`.
- **Etiquetas humanas**: las clases `1..5` se traducen a etiquetas socioeconómicas legibles.
