"""Adaptador del modelo de clasificación usado por la app fuente de verdad."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from GCP.api.errors import InvalidFeatureError, ModelNotReadyError
from GCP.api.schemas import PredictRequest, PredictResponse, Probability

CLASS_LABELS: dict[int, str] = {
    1: "Baja Baja",
    2: "Baja Alta",
    3: "Media Baja",
    4: "Media Alta",
    5: "Alta",
}

DEFAULT_FEATURE_ORDER = ["p126d", "p131", "p125d", "p126f", "p126g", "p125e", "p129a", "p125a", "p126b"]


@dataclass(frozen=True)
class PredictionModel:
    """Modelo cargado y metadatos necesarios para inferencia."""

    estimator: Any
    model_path: Path
    feature_order: list[str]

    @property
    def version(self) -> str:
        return self.model_path.name


class ModelService:
    """Carga el artefacto joblib y expone predicciones con contrato estable."""

    def __init__(self, model_path: Path | str):
        self.model_path = Path(model_path)
        self._model: PredictionModel | None = None

    def load(self) -> PredictionModel:
        """Carga el modelo bajo demanda y lo conserva en memoria del contenedor."""

        if self._model is not None:
            return self._model
        if not self.model_path.exists():
            raise ModelNotReadyError(f"No se encontró el modelo en {self.model_path}.")

        estimator = joblib.load(self.model_path)
        if not hasattr(estimator, "predict_proba"):
            raise ModelNotReadyError("El estimador no implementa predict_proba.")

        feature_order = list(getattr(estimator, "feature_names_in_", DEFAULT_FEATURE_ORDER))
        self._model = PredictionModel(estimator=estimator, model_path=self.model_path, feature_order=feature_order)
        return self._model

    def readiness(self) -> dict[str, str | int]:
        """Verifica que el modelo pueda cargarse y reporta metadatos mínimos."""

        model = self.load()
        return {
            "status": "ready",
            "model_version": model.version,
            "features": len(model.feature_order),
        }

    def predict(self, request: PredictRequest) -> PredictResponse:
        """Predice probabilidades de clase socioeconómica para un conjunto de variables."""

        model = self.load()
        supplied = set(request.features)
        known = set(model.feature_order)
        unknown = sorted(supplied - known)
        if unknown:
            raise InvalidFeatureError(f"Variables no reconocidas por el modelo: {', '.join(unknown)}.")

        row = {feature: float(request.features.get(feature, 0)) for feature in model.feature_order}
        frame = pd.DataFrame([row], columns=model.feature_order)
        probabilities = np.asarray(model.estimator.predict_proba(frame)[0], dtype=float)
        classes = list(getattr(model.estimator, "classes_", range(1, len(probabilities) + 1)))
        max_index = int(np.argmax(probabilities))
        predicted_class = _json_safe_class(classes[max_index])

        response_probabilities = [
            Probability(
                class_id=_json_safe_class(class_value),
                label=_label_for_class(class_value),
                probability=float(probability),
            )
            for class_value, probability in zip(classes, probabilities, strict=True)
        ]
        return PredictResponse(
            request_id=request.request_id,
            predicted_class=predicted_class,
            predicted_label=_label_for_class(classes[max_index]),
            predicted_probability=float(probabilities[max_index]),
            probabilities=response_probabilities,
            model_version=model.version,
            feature_order=model.feature_order,
        )


def _json_safe_class(value: Any) -> int | str:
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        as_float = float(value)
        return int(as_float) if as_float.is_integer() else str(as_float)
    return value if isinstance(value, int | str) else str(value)


def _label_for_class(value: Any) -> str:
    safe_value = _json_safe_class(value)
    if isinstance(safe_value, int):
        return CLASS_LABELS.get(safe_value, str(safe_value))
    return str(safe_value)
