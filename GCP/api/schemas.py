"""Contratos Pydantic de entrada y salida para la API."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PredictRequest(BaseModel):
    """Solicitud de predicción con variables codificadas como columnas del modelo."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={
        "examples": [
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
                    "p126b": 1,
                },
            }
        ]
    })

    request_id: str | None = Field(default=None, description="Identificador opcional de trazabilidad del consumidor.")
    features: dict[str, float | int | bool] = Field(..., min_length=1, description="Variables del modelo por nombre de columna.")

    @field_validator("features")
    @classmethod
    def validate_feature_names(cls, value: dict[str, float | int | bool]) -> dict[str, float | int | bool]:
        invalid = [key for key in value if not key or not key.strip()]
        if invalid:
            raise ValueError("Los nombres de variables no pueden estar vacíos.")
        return value


class Probability(BaseModel):
    """Probabilidad asociada a una clase del modelo."""

    class_id: int | str = Field(..., description="Clase original reportada por el modelo.")
    label: str = Field(..., description="Etiqueta legible de clase socioeconómica.")
    probability: float = Field(..., ge=0, le=1, description="Probabilidad normalizada entre 0 y 1.")


class PredictResponse(BaseModel):
    """Respuesta de predicción de clase socioeconómica."""

    request_id: str | None = None
    predicted_class: int | str
    predicted_label: str
    predicted_probability: float = Field(..., ge=0, le=1)
    probabilities: list[Probability]
    model_version: str
    feature_order: list[str]


class HealthResponse(BaseModel):
    """Estado operativo simple."""

    status: str
    service: str
    version: str
    environment: str


class ErrorResponse(BaseModel):
    """Formato estable de errores controlados."""

    error: str
    detail: str | list[dict[str, Any]]
