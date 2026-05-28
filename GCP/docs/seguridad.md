# Seguridad

## Autenticación y autorización

El manifiesto de ejemplo permite tráfico público para facilitar pruebas. En producción se recomienda una de estas opciones:

- Cloud Run privado con IAM (`roles/run.invoker`) para consumidores autenticados.
- API Gateway o Apigee delante del servicio.
- Validación de identidad con tokens OIDC emitidos por Google Cloud.

## Datos de entrada

- El contrato recibe variables codificadas del modelo, no información personal directa.
- Aun así, los payloads pueden ser sensibles por inferencia; deben tratarse como datos confidenciales.
- No registrar payloads completos en logs de aplicación.

## Red y CORS

- Mantener `MSMX_API_CORS_ORIGINS` vacío salvo que exista un frontend web autorizado.
- Si se habilita CORS, usar orígenes explícitos y no comodines en producción.

## Modelo y cadena de suministro

- Versionar imágenes con tags inmutables o digest SHA.
- Proteger el artefacto `joblib` contra escritura no autorizada.
- Escanear vulnerabilidades de dependencias durante CI/CD.
- Validar cambios de modelo con pruebas de contrato antes de promover a producción.

## Principio de mínimo privilegio

La cuenta de servicio de Cloud Run sólo necesita permisos para ejecutar el contenedor y leer recursos explícitamente requeridos. Si el modelo se empaqueta en la imagen, no requiere permisos de lectura a buckets durante runtime.
