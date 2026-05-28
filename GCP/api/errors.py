"""Errores de dominio y handlers HTTP."""

from typing import Any


class ModelServiceError(RuntimeError):
    """Error base del servicio de modelo."""


class ModelNotReadyError(ModelServiceError):
    """El modelo no puede atender predicciones."""


class InvalidFeatureError(ModelServiceError):
    """La solicitud no contiene variables compatibles con el modelo."""


def register_exception_handlers(app: Any) -> None:
    """Registra respuestas JSON consistentes para errores esperados."""

    from fastapi import Request, status
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse

    from GCP.api.schemas import ErrorResponse

    @app.exception_handler(ModelNotReadyError)
    async def model_not_ready_handler(_: Request, exc: ModelNotReadyError) -> JSONResponse:
        payload = ErrorResponse(error="model_not_ready", detail=str(exc))
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=payload.model_dump())

    @app.exception_handler(InvalidFeatureError)
    async def invalid_feature_handler(_: Request, exc: InvalidFeatureError) -> JSONResponse:
        payload = ErrorResponse(error="invalid_features", detail=str(exc))
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=payload.model_dump())

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        payload = ErrorResponse(error="validation_error", detail=exc.errors())
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=payload.model_dump())
